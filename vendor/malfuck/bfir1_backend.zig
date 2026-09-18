const std = @import("std");

pub const Op = enum(u8) {
    move_right = 1,
    move_left = 2,
    increment = 3,
    decrement = 4,
    output = 5,
    input = 6,
    jump_if_zero = 7,
    jump_if_nonzero = 8,
};

pub const Instruction = struct {
    op: Op,
    target: ?usize = null,
    source_pos: usize = 0,
};

pub const BackendError = error{
    InvalidHeader,
    InvalidLength,
    InvalidOpcode,
    InvalidFlags,
    UnexpectedBranch,
    UnmatchedBracket,
    OutOfMemory,
};

pub const Image = struct {
    code: std.ArrayListUnmanaged(Instruction) = .empty,

    pub fn deinit(self: *Image, allocator: std.mem.Allocator) void {
        self.code.deinit(allocator);
    }
};

pub const Lowered = struct {
    source: std.ArrayListUnmanaged(u8) = .empty,

    pub fn deinit(self: *Lowered, allocator: std.mem.Allocator) void {
        self.source.deinit(allocator);
    }

    pub fn slice(self: *const Lowered) []const u8 {
        return self.source.items;
    }
};

const Header = "BFIR1";
const RecordSize = 12;

pub fn decode(bytes: []const u8, allocator: std.mem.Allocator) BackendError!Image {
    if (bytes.len < Header.len + 4 or !std.mem.eql(u8, bytes[0..Header.len], Header)) {
        return error.InvalidHeader;
    }
    const count = std.mem.readInt(u32, bytes[Header.len..][0..4], .little);
    const payload = Header.len + 4;
    if (count > (bytes.len - payload) / RecordSize or
        payload + @as(usize, count) * RecordSize != bytes.len)
    {
        return error.InvalidLength;
    }

    var image = Image{};
    errdefer image.deinit(allocator);
    try image.code.ensureTotalCapacity(allocator, @intCast(count));
    var offset = payload;
    var index: usize = 0;
    while (index < count) : (index += 1) {
        const op = decodeOp(bytes[offset]) orelse return error.InvalidOpcode;
        if (bytes[offset + 1] > 1 or bytes[offset + 2] != 0 or bytes[offset + 3] != 0) {
            return error.InvalidFlags;
        }
        const target_value = std.mem.readInt(u32, bytes[offset + 4 ..][0..4], .little);
        const source_pos = std.mem.readInt(u32, bytes[offset + 8 ..][0..4], .little);
        try image.code.append(allocator, .{
            .op = op,
            .target = if (bytes[offset + 1] == 1) @intCast(target_value) else null,
            .source_pos = @intCast(source_pos),
        });
        offset += RecordSize;
    }
    return image;
}

fn decodeOp(value: u8) ?Op {
    return switch (value) {
        1 => .move_right,
        2 => .move_left,
        3 => .increment,
        4 => .decrement,
        5 => .output,
        6 => .input,
        7 => .jump_if_zero,
        8 => .jump_if_nonzero,
        else => null,
    };
}

pub const BracketMap = std.AutoHashMap(usize, usize);

pub fn buildBracketMap(image: *const Image, allocator: std.mem.Allocator) BackendError!BracketMap {
    var map = BracketMap.init(allocator);
    errdefer map.deinit();
    var stack = std.array_list.Managed(usize).init(allocator);
    defer stack.deinit();

    for (image.code.items, 0..) |instruction, index| {
        switch (instruction.op) {
            .jump_if_zero => try stack.append(index),
            .jump_if_nonzero => {
                if (stack.items.len == 0) return error.UnmatchedBracket;
                const open = stack.pop().?;
                try map.put(open, index);
                try map.put(index, open);
            },
            else => {},
        }
    }
    if (stack.items.len != 0) return error.UnmatchedBracket;
    return map;
}

pub fn lowerLinear(image: *const Image, allocator: std.mem.Allocator) BackendError!Lowered {
    var lowered = Lowered{};
    errdefer lowered.deinit(allocator);
    try lowered.source.appendSlice(allocator, ".CODE\n");
    try lowered.source.appendSlice(allocator, "  TAPE_BASE\n");

    for (image.code.items) |instruction| {
        switch (instruction.op) {
            .increment => {
                try lowered.source.appendSlice(allocator, "  INC\n  D_REWIND\n");
                continue;
            },
            .decrement => {
                try lowered.source.appendSlice(allocator, "  DEC\n  D_REWIND\n");
                continue;
            },
            .output => {
                try lowered.source.appendSlice(allocator, "  LOAD_D\n  D_REWIND\n  OUT\n  D_REWIND\n");
                continue;
            },
            .input => {
                try lowered.source.appendSlice(allocator, "  IN\n  D_REWIND\n  STORE\n  D_REWIND\n");
                continue;
            },
            .jump_if_zero, .jump_if_nonzero => return error.UnexpectedBranch,
            else => {},
        }
        const mnemonic: []const u8 = switch (instruction.op) {
            .move_right => "NOP",
            .move_left => "D_LEFT",
            else => unreachable,
        };
        try lowered.source.appendSlice(allocator, "  ");
        try lowered.source.appendSlice(allocator, mnemonic);
        try lowered.source.append(allocator, '\n');
    }
    try lowered.source.appendSlice(allocator, "  HALT\n");
    return lowered;
}

pub fn lowerBranched(image: *const Image, allocator: std.mem.Allocator) BackendError!Lowered {
    var lowered = Lowered{};
    errdefer lowered.deinit(allocator);

    var bracket_map = try buildBracketMap(image, allocator);
    defer bracket_map.deinit();

    // Compute the emitted cell position of every source instruction, so the
    // branch immediates can carry absolute code addresses.
    const n = image.code.items.len;
    const pos = try allocator.alloc(usize, n + 1);
    defer allocator.free(pos);
    var cell: usize = 1; // position 0 = TAPE_BASE
    for (image.code.items, 0..) |instruction, index| {
        pos[index] = cell;
        cell += expansionSize(instruction.op);
    }
    pos[n] = cell; // address of HALT

    try lowered.source.appendSlice(allocator, ".CODE\n");
    try lowered.source.appendSlice(allocator, "  TAPE_BASE\n");

    for (image.code.items, 0..) |instruction, index| {
        switch (instruction.op) {
            .move_right => try lowered.source.appendSlice(allocator, "  NOP\n"),
            .move_left => try lowered.source.appendSlice(allocator, "  D_LEFT\n"),
            .increment => try lowered.source.appendSlice(allocator, "  INC\n  D_REWIND\n"),
            .decrement => try lowered.source.appendSlice(allocator, "  DEC\n  D_REWIND\n"),
            .output => try lowered.source.appendSlice(allocator, "  LOAD_D\n  D_REWIND\n  OUT\n  D_REWIND\n"),
            .input => try lowered.source.appendSlice(allocator, "  IN\n  D_REWIND\n  STORE\n  D_REWIND\n"),
            .jump_if_zero => {
                const target_index = bracket_map.get(index) orelse return error.UnmatchedBracket;
                // BF `[`: if cell==0, skip to the instruction after matching `]`.
                const target = pos[target_index] + expansionSize(image.code.items[target_index].op);
                try lowered.source.appendSlice(allocator, "  JZ\n");
                try writeImm94(&lowered, allocator, target);
            },
            .jump_if_nonzero => {
                const target_index = bracket_map.get(index) orelse return error.UnmatchedBracket;
                // BF `]`: if cell!=0, jump back to the matching `[`.
                const target = pos[target_index];
                try lowered.source.appendSlice(allocator, "  JNZ\n");
                try writeImm94(&lowered, allocator, target);
            },
        }
    }
    try lowered.source.appendSlice(allocator, "  HALT\n");
    return lowered;
}

fn expansionSize(op: Op) usize {
    return switch (op) {
        .move_right, .move_left => 1,
        .increment, .decrement => 2,
        .output, .input => 4,
        .jump_if_zero, .jump_if_nonzero => 4,
    };
}

fn writeImm94(lowered: *Lowered, allocator: std.mem.Allocator, value: usize) !void {
    var v = value;
    const d2 = v % 94;
    v /= 94;
    const d1 = v % 94;
    v /= 94;
    const d0 = v % 94;
    const digits = [3]usize{ d0, d1, d2 };
    for (digits) |digit| {
        try lowered.source.appendSlice(allocator, "  ");
        try writeUsint(lowered, allocator, digit + 33);
        try lowered.source.append(allocator, '\n');
    }
}

fn writeUsint(lowered: *Lowered, allocator: std.mem.Allocator, value: usize) !void {
    var buf: [20]u8 = undefined;
    var len: usize = 0;
    var v = value;
    if (v == 0) {
        buf[0] = '0';
        len = 1;
    } else {
        while (v > 0) : (v /= 10) {
            buf[len] = @intCast('0' + (v % 10));
            len += 1;
        }
        std.mem.reverse(u8, buf[0..len]);
    }
    try lowered.source.appendSlice(allocator, buf[0..len]);
}

pub fn lowerImage(bytes: []const u8, allocator: std.mem.Allocator) BackendError!Lowered {
    var image = try decode(bytes, allocator);
    defer image.deinit(allocator);
    for (image.code.items) |instruction| {
        if (instruction.op == .jump_if_zero or instruction.op == .jump_if_nonzero) {
            return lowerBranched(&image, allocator);
        }
    }
    return lowerLinear(&image, allocator);
}
