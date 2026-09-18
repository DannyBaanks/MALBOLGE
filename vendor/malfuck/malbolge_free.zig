//! MALBOLGE_FREE_V0 — parametric Malbolge core in Zig.
//!
//! Semantics: ONE core, parameterized by `width` (trits) and `MemPolicy`.
//! No hardcoded 3^10 / 3^19. No `if k == 10` or `if k == 19` branches anywhere.
//!
//!   Classic    = width 10, mem_limit = 3^10 (eager crazy-fill semantics),
//!                fixed width (growth_policy = .fixed)
//!   Unshackled = width starts at 10.growth via rotate-pad (deterministic
//!                det_growth_policy from Unshackled.c), lazy memory, Unicode-ish
//!                I/O suppressed here (byte I/O for instrumentation).
//!   Free       = unbounded memory (mem_limit = null), start width 10,
//!                w (= padwidth) widens by address frontier under the
//!                epochal policy: when c or d reaches 3^w, w += 1.
//!
//! Values: u128. Width bound: floor(log_3(2^127)) = 80.
//! For k <= 80 all trit ops are exact. That covers k in {10..26} (crossing
//! 3^19 needs only 20). Arbitrary-k via BigInt is a FUTURE decision.
//! w is a plain finite integer at every executed step — nothing infinite
//! is claimed anywhere in this file.

const std = @import("std");
const Allocator = std.mem.Allocator;

/// crazy table CRZ[a][b] (from Classic spec / Iizawa 2005 / 1998 malbolge.c)
const CRZ = [3][3]u3{
    .{ 1, 0, 0 },
    .{ 1, 0, 2 },
    .{ 2, 2, 1 },
};

/// encryption table (original -> translated), from Classic spec
pub const ORIGINAL = "!\"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~";
pub const TRANSLATED = "5z]&gqtyfr$(we4{WP)H-Zn,[%\\3dL+Q;>U!pJS72FhOA1CB6v^=I_0/8|jsb9m<.TVac`uY*MK'X~xDl}REokN:#?G\"i@";

/// tritwise crazy over exactly `width` trits.
pub fn crazy(a0: u128, b0: u128, width: u8) u128 {
    var a = a0;
    var b = b0;
    var res: u128 = 0;
    var p: u128 = 1;
    var i: u8 = 0;
    while (i < width) : (i += 1) {
        res += @as(u128, CRZ[@intCast(b % 3)][@intCast(a % 3)]) * p;
        a /= 3;
        b /= 3;
        p *= 3;
    }
    return res;
}

/// rotate right one trit within `width` trits.
pub fn rotate(v: u128, width: u8) u128 {
    const p = pow3(width - 1);
    return v / 3 + (v % 3) * p;
}

/// 3^n — exact for n <= 80. 3^81 does not fit in u128.
/// Widths above 80 are outside the defined runtime and saturate here so
/// callers cannot mistake an overflowing value for an exact power.
pub fn pow3(n: u8) u128 {
    if (n >= 81) return std.math.maxInt(u128);
    var p: u128 = 1;
    var i: u8 = 0;
    while (i < n) : (i += 1) p *= 3;
    return p;
}

/// minimal trits required to express v (0 = 1 trit).
pub fn tritlen(v0: u128) u8 {
    var v = v0;
    var n: u8 = 1;
    while (v >= 3) : (v /= 3) n += 1;
    return n;
}

/// EOF sentinel. Never stored in memory; normalized at op use sites.
pub const EOF_SENTINEL: u128 = std.math.maxInt(u128);

pub const GrowthPolicy = enum {
    /// Classic: width frozen at `width`.
    fixed,
    /// Legacy probing mode. Not semantically defended; see F8.
    pad_to_padwidth,
    /// ANCHORED / EPOCHAL WIDENING.
    ///
    /// Rules (this is a distinct machine, not "M_k postponed"):
    ///   1. state carries the current width `padwidth` (docs call it `w`;
    ///      always a concrete finite integer);
    ///   2. rotate/crazy use `padwidth` just like `fixed` uses `width`;
    ///   3. ACTUAL TRIGGER (address frontier): when `c` or `d` reaches
    ///      `3^padwidth` — possible because unbounded mode never wraps the
    ///      pointers — `frontierTrigger` bumps `padwidth` by 1 BEFORE the
    ///      step executes and logs a `WIDEN` event (see `run`);
    ///   4. widening never touches any previously written cell, stdout byte,
    ///      steps count, or any other historical observables;
    ///   5. `padwidth` is monotonically non-decreasing;
    ///   6. a VALUE-based trigger (widen when an op result would not fit)
    ///      can never fire: no op at width k produces a value wider than k
    ///      trits (see docs/EPOCHAL_ANALYSIS.md). `widenIfNeeded` below is
    ///      retained for evidence only and is not called by `run`.
    ///
    /// Invariants verified (see tests/epochal.zig):
    ///   - P1 prefix preservation: until first WIDEN, trace equals `fixed` run
    ///     at the initial width
    ///   - P2 anchor preservation: the memory map just before and after the
    ///     WIDEN event is identical
    ///   - P3 no replay: step count keeps increasing monotonically
    ///   - P4 determinism: same program and seed => same widen positions
    ///   - P6 degeneration: absent a widen trigger, run == `fixed` run
    epochal,
};

/// Execution profile. `free_assisted` preserves the existing BF substrate;
/// `classic` and `free_pure` accept only positional Classic source opcodes.
pub const ExecutionProfile = enum {
    classic,
    free_pure,
    free_assisted,
};

pub const tritlen2 = tritlen; pub const rotate2 = rotate; pub const crazy2 = crazy; pub const pow3_ = pow3; pub const RunResult = struct {
    status: []const u8, // "HALTED" | "MAX_STEPS"
    steps: u64,
    stdout: std.ArrayList(u8),
    max_addr_touched: u128,
    max_value: u128,
    cells_materialized: u32,
    final_c: u128,
    final_d: u128,
    assisted_opcodes: u32,
    encrypted_cells: u32,
};

pub const TraceEvent = struct {
    step: u64,
    a_before: u128,
    c_before: u128,
    d_before: u128,
    op: u128,
    cell_before: u128,
    a_after: u128,
    c_after: u128,
    d_after: u128,
    encrypted_addr: ?u128,
    encrypted_value: ?u128,
};

pub const MalbolgeCore = struct {
    alloc: Allocator,
    width: u8,
    mem_limit: ?u128, // None => unbounded (no wrap at all)
    growth: GrowthPolicy,
    profile: ExecutionProfile,
    padwidth: u8,
    mem: std.AutoHashMap(u128, u128),
    program_len: u128,
    lock_noencrypt: bool = false,
    stats: struct {
        max_addr: u128 = 0,
        max_value: u128 = 0,
        growth_events: u32 = 0,
    },

    pub fn init(alloc: Allocator, width: u8, mem_limit: ?u128, growth: GrowthPolicy) MalbolgeCore {
        std.debug.assert(width >= 1 and width <= 80);
        return .{
            .alloc = alloc,
            .width = width,
            .mem_limit = mem_limit,
            .growth = growth,
            // Backward-compatible constructor for the existing assisted
            // Free/BF substrate. Strict profiles use the named constructors.
            .profile = .free_assisted,
            .padwidth = width,
            .mem = std.AutoHashMap(u128, u128).init(alloc),
            .program_len = 0,
            .stats = .{},
        };
    }

    pub fn initClassic(alloc: Allocator) MalbolgeCore {
        var self = init(alloc, 10, pow3(10), .fixed);
        self.profile = .classic;
        return self;
    }

    pub fn initFreeAssisted(alloc: Allocator, width: u8, mem_limit: ?u128, growth: GrowthPolicy) MalbolgeCore {
        return init(alloc, width, mem_limit, growth);
    }

    pub fn initFreePure(alloc: Allocator, width: u8, growth: GrowthPolicy) MalbolgeCore {
        var self = init(alloc, width, null, growth);
        self.profile = .free_pure;
        return self;
    }

    pub fn deinit(self: *MalbolgeCore) void {
        self.mem.deinit();
    }

    /// Loader: strip whitespace, enforce printable range, store program cells.
    pub fn load(self: *MalbolgeCore, source: []const u8) !void {
        var i: u128 = 0;
        for (source) |ch| {
            if (ch == ' ' or ch == '\t' or ch == '\r' or ch == '\n') continue;
            if (ch < 33 or ch > 126) return error.InvalidSource;
            if (self.profile != .free_assisted and !isClassicSourceOpcode(ch, i)) {
                return error.InvalidSourceOpcode;
            }
            try self.mem.put(i, ch);
            i += 1;
        }
        if (i < 2) return error.ProgramTooShort;
        self.program_len = i;
    }

    fn isClassicSourceOpcode(ch: u8, position: u128) bool {
        return switch ((@as(u128, ch) + position) % 94) {
            4, 5, 23, 39, 40, 62, 68, 81 => true,
            else => false,
        };
    }

    fn touch(self: *MalbolgeCore, addr: u128) void {
        if (addr > self.stats.max_addr) self.stats.max_addr = addr;
    }

    /// Lazy read with Classic crazy-fill semantics:
    ///   cell[i] = crazy(cell[i-1], cell[i-2])   for i >= program_len
    /// The tail is filled lazily with the exact recurrence. Do not shortcut it
    /// with a presumed period: execution may encrypt or overwrite a tail cell,
    /// so a cycle cache can return stale values after a jump.
    pub fn cell(self: *MalbolgeCore, addr0: u128) !u128 {
        var i = addr0;
        if (self.mem_limit) |lim| i %= lim;
        self.touch(i);
        if (self.mem.get(i)) |v| return v;

        // Manifest only the region the runtime actually queries.
        var t = self.program_len;
        while (t <= i) : (t += 1) {
            if (self.mem.get(t) != null) continue;
            const v1 = self.mem.get(t - 1) orelse return error.InvalidLoad;
            const v2 = self.mem.get(t - 2) orelse return error.InvalidLoad;
            try self.mem.put(t, crazy(v1, v2, self.width));
        }
        return self.mem.get(i).?;
    }

    pub fn cellWrite(self: *MalbolgeCore, addr0: u128, v: u128) !void {
        var i = addr0;
        if (self.mem_limit) |lim| i %= lim;
        self.touch(i);
        if (v > self.stats.max_value) self.stats.max_value = v;
        try self.mem.put(i, v);
    }

    /// Read a 3-digit big-endian base-94 immediate stored in cells c+1..c+3.
    /// Each digit cell holds a printable value 33..126; digit = value - 33.
    fn readImm94(self: *MalbolgeCore, c0: u128) !u128 {
        const base = if (self.mem_limit) |lim| c0 % lim else c0;
        var target: u128 = 0;
        var i: u128 = 1;
        while (i <= 3) : (i += 1) {
            const v = try self.cell(base + i);
            const digit: u128 = if (v >= 33 and v <= 126) v - 33 else 0;
            target = target * 94 + digit;
        }
        return target;
    }

    /// Effective rotate width under each policy.
    pub fn rotWidthFor(self: *MalbolgeCore, v: u128) u8 {
        return switch (self.growth) {
            .fixed => self.width,
            .pad_to_padwidth => @max(self.padwidth, tritlen(v)),
            .epochal => self.padwidth,
        };
    }

    /// Legacy pad-to-padwidth growth (kept for evidence, not semantics).
    pub fn maybeGrow(self: *MalbolgeCore, v: u128) void {
        if (self.growth != .pad_to_padwidth) return;
        const need = tritlen(v);
        if (need > self.padwidth) {
            self.padwidth = need;
            self.stats.growth_events += 1;
        }
    }

    /// Epochal preflight: if `v` doesn't fit in the current epoch width, widen
    /// prior to the op. Logs a WIDEN event into growth_events (monotonic).
    pub     fn widenIfNeeded(self: *MalbolgeCore, v: u128) void {
        if (self.growth != .epochal) return;
        const need = tritlen(v);
        if (need > self.padwidth) {
            self.padwidth = need;
            self.stats.growth_events += 1;
        }
    }

    /// FRONTIER TRIGGER: widen when the ADDRESS of c or d reaches 3^w.
    /// A value-based trigger can never fire (docs/EPOCHAL_ANALYSIS.md), but
    /// in unbounded mode the pointers advance one cell per step and DO reach
    /// the frontier. Measured once: WIDEN at c = 3^10, w: 10 -> 11
    /// (tests/t_frontier_moment.zig).
    ///
    /// Contract:
    ///   - fires when c or d is about to reach `3^padwidth`
    ///   - anchor position: snapshot BEFORE the read touches memory at that
    ///     address
    ///   - result: padwidth bumps by exactly 1 (monotonic)
    ///   - prefix preservation: before the trigger, all reads saw k = base width
    pub fn frontierTrigger(self: *MalbolgeCore, c: u128, d: u128) void {
        if (self.growth != .epochal) return;
        const boundary = pow3(self.padwidth);
        if (c >= boundary or d >= boundary) {
            self.padwidth += 1;
            self.stats.growth_events += 1; // WIDEN (anchor epoch closed at this step)
        }
    }

    /// Run up to max_steps. I/O is byte-oriented for cross-runtime parity
    /// (Classic-compatible). Unicode I/O from Unshackled is out of scope here.
    pub fn run(self: *MalbolgeCore, max_steps: u64, stdin_data: []const u8) !RunResult {
        return self.runInternal(max_steps, stdin_data, null);
    }

    pub fn runWithTrace(self: *MalbolgeCore, max_steps: u64, stdin_data: []const u8, trace: *std.ArrayList(TraceEvent)) !RunResult {
        return self.runInternal(max_steps, stdin_data, trace);
    }

    fn runInternal(self: *MalbolgeCore, max_steps: u64, stdin_data: []const u8, trace: ?*std.ArrayList(TraceEvent)) !RunResult {
        var a: u128 = 0;
        var c: u128 = 0;
        var d: u128 = 0;
        var out = std.ArrayList(u8).empty;
        var stdin_idx: usize = 0;
        var steps: u64 = 0;
        var assisted_opcodes: u32 = 0;
        var encrypted_cells: u32 = 0;

        const status: []const u8 = blk: {
            while (steps < max_steps) {
                steps += 1;
                // EPOCHAL WIDEN CHECK: trigger BEFORE touching a memory cell whose
                // address exceeds the current width boundary. This is where
                // Danny's "execution frontier" idea lives in the code.
                self.frontierTrigger(c, d);

                const cc = if (self.mem_limit) |lim| c % lim else c;
                const cellv = try self.cell(cc);
                const op = (cellv + cc) % 94;
                const a_before = a;
                const c_before = c;
                const d_before = d;
                var halted = false;
                var encrypted_addr: ?u128 = null;
                var encrypted_value: ?u128 = null;
                if (self.profile == .free_assisted and op >= 69 and op <= 79) {
                    assisted_opcodes += 1;
                }
                // The BF substrate is opt-in. In strict profiles, extension
                // opcodes are ordinary runtime NOPs, as they are in Classic.
                const effective_op = if (self.profile != .free_assisted and op >= 69 and op <= 79) 68 else op;

                switch (effective_op) {
                    4 => { // jmp
                        const dd = if (self.mem_limit) |lim| d % lim else d;
                        c = try self.cell(dd);
                    },
                    5 => { // out
                        try out.append(self.alloc, @intCast(a % 256));
                    },
                    23 => { // in
                        if (stdin_idx < stdin_data.len) {
                            a = stdin_data[stdin_idx];
                            stdin_idx += 1;
                        } else {
                            a = EOF_SENTINEL;
                        }
                    },
                    39 => { // rot
                        const dd = if (self.mem_limit) |lim| d % lim else d;
                        const v = try self.cell(dd);
                        const w = self.rotWidthFor(v);
                        const nv = rotate(v, w);
                        try self.cellWrite(dd, nv);
                        a = nv;
                        self.maybeGrow(a);
                    },
                    40 => { // movd
                        const dd = if (self.mem_limit) |lim| d % lim else d;
                        d = try self.cell(dd);
                        self.maybeGrow(d);
                    },
                    62 => { // crazy op
                        const dd = if (self.mem_limit) |lim| d % lim else d;
                        const v = try self.cell(dd);
                        const w: u8 = switch (self.growth) {
                            .fixed => self.width,
                            .pad_to_padwidth => @min(79, @max(@max(self.padwidth, tritlen(v)), tritlen(@min(a, @as(u128, 1) << 126)))),
                            .epochal => self.padwidth,
                        };
                        const modulus: u128 = pow3(w);
                        const opA = if (a == EOF_SENTINEL) modulus - 1 else (a % modulus);
                        const nv = crazy(opA, v, w);
                        try self.cellWrite(dd, nv);
                        a = nv;
                    },
                    68 => {}, // nop
                    69 => { // read_d_0 — read cell[0] into accumulator
                        const v = try self.cell(0);
                        a = v;
                    },
                    70 => { // jmp_a — jump to address in accumulator
                        // EOF_SENTINEL is never a valid address (it would
                        // overflow c+1 in unbounded mode); normalize to 0,
                        // mirroring how OPR normalizes it to modulus-1.
                        c = if (a == EOF_SENTINEL) 0 else a;
                    },
                    71 => { // inc — increment cell[d] modulo 256 (BF semantics)
                        const dd = if (self.mem_limit) |lim| d % lim else d;
                        const v = try self.cell(dd);
                        const nv = (v + 1) % 256;
                        try self.cellWrite(dd, nv);
                        a = nv;
                    },
                    72 => { // dec — decrement cell[d] modulo 256 (BF semantics)
                        const dd = if (self.mem_limit) |lim| d % lim else d;
                        const v = try self.cell(dd);
                        const nv = (v + 255) % 256;
                        try self.cellWrite(dd, nv);
                        a = nv;
                    },
                    73 => { // load_d — a = cell[d] without modifying the cell
                        const dd = if (self.mem_limit) |lim| d % lim else d;
                        a = try self.cell(dd);
                    },
                    74 => { // store — cell[d] = a (byte-wrapped, EOF -> 0)
                        const dd = if (self.mem_limit) |lim| d % lim else d;
                        const v: u128 = if (a == EOF_SENTINEL) 0 else (a % 256);
                        try self.cellWrite(dd, v);
                    },
75 => { // tape_base — enter the data tape at a stable address
                        var tape_index: u128 = 0;
                        while (tape_index < 256) : (tape_index += 1) {
                            try self.cellWrite(1000 + tape_index, 0);
                        }
                        // The Free substrate is stable: from here on, Free
                        // opcodes (69..79) are not self-encrypted. Classic
                        // opcodes keep Classic self-modification.
                        self.lock_noencrypt = true;
                        d = 999;
                    },
                    76 => { // d_rewind — compensate the post-step d increment
                        d = if (d >= 2) d - 2 else 0;
                    },
77 => { // d_left — move the logical BF pointer one cell left
                        d = if (d >= 2) d - 2 else 0;
                    },
                    78 => { // jz — if cell[d]==0, jump to the base-94 immediate at c+1..c+3
                        const target = try self.readImm94(c);
                        const dd = if (self.mem_limit) |lim| d % lim else d;
                        const cv = try self.cell(dd);
                        d = if (d >= 1) d - 1 else 0;
                        if (cv == 0) {
                            c = if (target >= 1) target - 1 else 0;
                        } else {
                            c = c + 3;
                        }
                    },
                    79 => { // jnz — if cell[d]!=0, jump to the base-94 immediate
                        const target = try self.readImm94(c);
                        const dd = if (self.mem_limit) |lim| d % lim else d;
                        const cv = try self.cell(dd);
                        d = if (d >= 1) d - 1 else 0;
                        if (cv != 0) {
                            c = if (target >= 1) target - 1 else 0;
                        } else {
                            c = c + 3;
                        }
                    },
                    81 => halted = true,
                    else => {}, // invalid => nop
                }

                if (halted) {
                    if (trace) |events| try events.append(self.alloc, .{
                        .step = steps, .a_before = a_before, .c_before = c_before,
                        .d_before = d_before, .op = op, .cell_before = cellv,
                        .a_after = a, .c_after = c, .d_after = d,
                        .encrypted_addr = null, .encrypted_value = null,
                    });
                    break :blk "HALTED";
                }

                // self-encryption on the cell we just stepped on. Once
                // TAPE_BASE has armed the stable Free substrate, self-
                // modification is disabled entirely (Free programs are a
                // stable substrate; they use explicit jumps, not self-
                // modifying trampolines). Classic programs never execute
                // TAPE_BASE, so Classic parity is untouched.
                if (!self.lock_noencrypt) {
                    const cc2 = if (self.mem_limit) |lim| c % lim else c;
                    const mc = try self.cell(cc2);
                    if (mc >= 33 and mc <= 126) {
                        const idx: usize = @intCast(mc - 33);
                        const enc = TRANSLATED[idx];
                        try self.cellWrite(cc2, enc);
                        encrypted_cells += 1;
                        encrypted_addr = cc2;
                        encrypted_value = enc;
                    }
                }

                c = if (self.mem_limit) |lim| (c + 1) % lim else c + 1;
                d = if (self.mem_limit) |lim| (d + 1) % lim else d + 1;
                if (trace) |events| try events.append(self.alloc, .{
                    .step = steps, .a_before = a_before, .c_before = c_before,
                    .d_before = d_before, .op = op, .cell_before = cellv,
                    .a_after = a, .c_after = c, .d_after = d,
                    .encrypted_addr = encrypted_addr, .encrypted_value = encrypted_value,
                });
            }
            break :blk "MAX_STEPS";
        };

        return .{
            .status = status,
            .steps = steps,
            .stdout = out,
            .max_addr_touched = self.stats.max_addr,
            .max_value = self.stats.max_value,
            .cells_materialized = self.mem.count(),
            .final_c = c,
            .final_d = d,
            .assisted_opcodes = assisted_opcodes,
            .encrypted_cells = encrypted_cells,
        };
    }

};
