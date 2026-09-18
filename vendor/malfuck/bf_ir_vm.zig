// bf_ir_vm.zig â€” executable reference for the lowered BF IR.
const std = @import("std");
const bf = @import("bf_reference.zig");
const ir = @import("bf_to_ir.zig");

pub fn run(
    program: *const ir.Program,
    input: []const u8,
    config: bf.Config,
    allocator: std.mem.Allocator,
    capture_trace: bool,
) !bf.Outcome {
    try ir.validate(program);
    if (config.tape_size == 0) return error.InvalidTapeSize;
    var tape = std.array_list.Managed(u8).init(allocator);
    errdefer tape.deinit();
    try tape.appendNTimes(0, config.tape_size);

    var output = std.array_list.Managed(u8).init(allocator);
    errdefer output.deinit();
    var trace = std.array_list.Managed(bf.TraceEvent).init(allocator);
    errdefer trace.deinit();

    var pc: usize = 0;
    var pointer: usize = 0;
    var input_pos: usize = 0;
    var steps: u64 = 0;
    while (pc < program.code.items.len) {
        if (steps == config.max_steps) return error.MaxStepsExceeded;
        const instruction = program.code.items[pc];
        steps += 1;
        switch (instruction.op) {
            .move_right => {
                if (pointer + 1 >= tape.items.len) return error.PointerOutOfBounds;
                pointer += 1;
            },
            .move_left => {
                if (pointer == 0) return error.PointerOutOfBounds;
                pointer -= 1;
            },
            .increment => tape.items[pointer] +%= 1,
            .decrement => tape.items[pointer] -%= 1,
            .output => try output.append(tape.items[pointer]),
            .input => {
                tape.items[pointer] = if (input_pos < input.len) input[input_pos] else 0;
                input_pos += 1;
            },
            .jump_if_zero => {
                if (tape.items[pointer] == 0) pc = instruction.target.?;
            },
            .jump_if_nonzero => {
                if (tape.items[pointer] != 0) pc = instruction.target.?;
            },
        }
        if (capture_trace) try trace.append(.{
            .step = steps,
            .pc = instruction.source_pos,
            .op = opByte(instruction.op),
            .pointer = pointer,
            .cell = tape.items[pointer],
            .input_pos = input_pos,
            .output_len = output.items.len,
        });
        pc += 1;
    }
    return .{ .output = output, .trace = trace, .tape = tape, .steps = steps, .pointer = pointer };
}

fn opByte(op: ir.Op) u8 {
    return switch (op) {
        .move_right => '>', .move_left => '<', .increment => '+', .decrement => '-',
        .output => '.', .input => ',', .jump_if_zero => '[', .jump_if_nonzero => ']',
    };
}

