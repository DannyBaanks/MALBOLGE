// bf_ir_image.zig — deterministic payload format for a future Malbolge VM.
const std = @import("std");
const ir = @import("bf_to_ir.zig");

pub const Header = "BFIR1";
const RecordSize = 12;

pub fn encode(program: *const ir.Program, allocator: std.mem.Allocator) ![]u8 {
    try ir.validate(program);
    const size = Header.len + 4 + program.code.items.len * RecordSize;
    var image = try allocator.alloc(u8, size);
    @memcpy(image[0..Header.len], Header);
    std.mem.writeInt(u32, image[Header.len..][0..4], @intCast(program.code.items.len), .little);

    var offset = Header.len + 4;
    for (program.code.items) |instruction| {
        image[offset] = opcode(instruction.op);
        image[offset + 1] = if (instruction.target != null) 1 else 0;
        image[offset + 2] = 0;
        image[offset + 3] = 0;
        std.mem.writeInt(u32, image[offset + 4 ..][0..4], @intCast(instruction.target orelse 0), .little);
        std.mem.writeInt(u32, image[offset + 8 ..][0..4], @intCast(instruction.source_pos), .little);
        offset += RecordSize;
    }
    return image;
}

pub fn decode(bytes: []const u8, allocator: std.mem.Allocator) !ir.Program {
    if (bytes.len < Header.len + 4 or !std.mem.eql(u8, bytes[0..Header.len], Header)) {
        return error.InvalidHeader;
    }
    const count = std.mem.readInt(u32, bytes[Header.len..][0..4], .little);
    const payload = Header.len + 4;
    if (count > (bytes.len - payload) / RecordSize or payload + @as(usize, count) * RecordSize != bytes.len) {
        return error.InvalidLength;
    }

    var code = std.array_list.Managed(ir.Instruction).init(allocator);
    errdefer code.deinit();
    try code.ensureTotalCapacity(@intCast(count));
    var offset = payload;
    var index: usize = 0;
    while (index < count) : (index += 1) {
        const op = decodeOpcode(bytes[offset]) orelse return error.InvalidOpcode;
        const has_target = bytes[offset + 1] == 1;
        if (bytes[offset + 1] > 1 or bytes[offset + 2] != 0 or bytes[offset + 3] != 0) {
            return error.InvalidFlags;
        }
        const target_value = std.mem.readInt(u32, bytes[offset + 4 ..][0..4], .little);
        const source_pos = std.mem.readInt(u32, bytes[offset + 8 ..][0..4], .little);
        try code.append(.{
            .op = op,
            .target = if (has_target) @as(usize, target_value) else null,
            .source_pos = @intCast(source_pos),
        });
        offset += RecordSize;
    }
    var program = ir.Program{ .code = code };
    errdefer program.deinit();
    try ir.validate(&program);
    return program;
}

fn decodeOpcode(value: u8) ?ir.Op {
    return switch (value) {
        1 => .move_right, 2 => .move_left, 3 => .increment, 4 => .decrement,
        5 => .output, 6 => .input, 7 => .jump_if_zero, 8 => .jump_if_nonzero,
        else => null,
    };
}

pub const Error = error{ InvalidHeader, InvalidLength, InvalidOpcode, InvalidFlags };

fn opcode(op: ir.Op) u8 {
    return switch (op) {
        .move_right => 1, .move_left => 2, .increment => 3, .decrement => 4,
        .output => 5, .input => 6, .jump_if_zero => 7, .jump_if_nonzero => 8,
    };
}
