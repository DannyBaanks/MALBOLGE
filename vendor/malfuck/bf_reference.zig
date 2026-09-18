// bf_interpreter.zig — executable Brainfuck reference semantics for M6.
const std = @import("std");

pub const TapeSize = 30_000;
pub const MaxSteps = 10_000_000;

pub const Config = struct {
    tape_size: usize = TapeSize,
    max_steps: u64 = MaxSteps,
};

pub const TraceEvent = struct {
    step: u64,
    pc: usize,
    op: u8,
    pointer: usize,
    cell: u8,
    input_pos: usize,
    output_len: usize,
};

pub const Outcome = struct {
    output: std.array_list.Managed(u8),
    trace: std.array_list.Managed(TraceEvent),
    tape: std.array_list.Managed(u8),
    steps: u64,
    pointer: usize,

    pub fn deinit(self: *Outcome) void {
        self.output.deinit();
        self.trace.deinit();
        self.tape.deinit();
    }
};

pub fn run(source: []const u8, input: []const u8, allocator: std.mem.Allocator) ![]u8 {
    var result = try runWithTrace(source, input, .{}, allocator, false);
    defer result.deinit();
    return try result.output.toOwnedSlice();
}

pub fn runWithTrace(
    source: []const u8,
    input: []const u8,
    config: Config,
    allocator: std.mem.Allocator,
    capture_trace: bool,
) !Outcome {
    if (config.tape_size == 0) return error.InvalidTapeSize;

    var tape = std.array_list.Managed(u8).init(allocator);
    errdefer tape.deinit();
    try tape.appendNTimes(0, config.tape_size);

    var brackets = std.AutoHashMap(usize, usize).init(allocator);
    defer brackets.deinit();
    var stack = std.array_list.Managed(usize).init(allocator);
    defer stack.deinit();
    for (source, 0..) |ch, i| {
        switch (ch) {
            '[' => try stack.append(i),
            ']' => {
                const open = stack.pop() orelse return error.UnmatchedBracket;
                try brackets.put(open, i);
                try brackets.put(i, open);
            },
            else => {},
        }
    }
    if (stack.items.len != 0) return error.UnmatchedBracket;

    var output = std.array_list.Managed(u8).init(allocator);
    errdefer output.deinit();
    var trace = std.array_list.Managed(TraceEvent).init(allocator);
    errdefer trace.deinit();

    var pc: usize = 0;
    var pointer: usize = 0;
    var input_pos: usize = 0;
    var steps: u64 = 0;
    while (pc < source.len) {
        const op = source[pc];
        if (!isInstruction(op)) {
            pc += 1;
            continue;
        }
        if (steps == config.max_steps) return error.MaxStepsExceeded;
        steps += 1;

        switch (op) {
            '>' => {
                if (pointer + 1 >= tape.items.len) return error.PointerOutOfBounds;
                pointer += 1;
            },
            '<' => {
                if (pointer == 0) return error.PointerOutOfBounds;
                pointer -= 1;
            },
            '+' => tape.items[pointer] +%= 1,
            '-' => tape.items[pointer] -%= 1,
            '.' => try output.append(tape.items[pointer]),
            ',' => {
                tape.items[pointer] = if (input_pos < input.len) input[input_pos] else 0;
                input_pos += 1;
            },
            '[' => {
                if (tape.items[pointer] == 0) pc = brackets.get(pc).?;
            },
            ']' => {
                if (tape.items[pointer] != 0) pc = brackets.get(pc).?;
            },
            else => unreachable,
        }

        if (capture_trace) try trace.append(.{
            .step = steps,
            .pc = pc,
            .op = op,
            .pointer = pointer,
            .cell = tape.items[pointer],
            .input_pos = input_pos,
            .output_len = output.items.len,
        });
        pc += 1;
    }

    return .{ .output = output, .trace = trace, .tape = tape, .steps = steps, .pointer = pointer };
}

fn isInstruction(ch: u8) bool {
    return switch (ch) {
        '>', '<', '+', '-', '.', ',', '[', ']' => true,
        else => false,
    };
}

pub const Error = error{
    InvalidTapeSize,
    UnmatchedBracket,
    MaxStepsExceeded,
    PointerOutOfBounds,
};
