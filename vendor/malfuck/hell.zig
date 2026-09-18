const std = @import("std");
const mem = std.mem;

pub const TokenType = enum {
    dot_code,
    dot_data,
    keyword_mov,
    keyword_movd,
    keyword_nop,
    keyword_in,
    keyword_out,
    keyword_opr,
    keyword_jmp,
    keyword_halt,
    keyword_read_d_0,
    keyword_jmp_a,
    keyword_inc,
    keyword_dec,
    keyword_load_d,
    keyword_store,
    keyword_tape_base,
    keyword_d_rewind,
    keyword_d_left,
    keyword_jz,
    keyword_jnz,
    keyword_flag,
    keyword_var,
    keyword_call,
    prefix_u,
    prefix_r,
    prefix_c,
    colon,
    lbrace,
    rbrace,
    slash,
    question,
    hash,
    minus,
    label,
    number,
    eol,
    eof,
};

pub const Token = struct {
    type: TokenType,
    lexeme: []const u8,
    line: usize,
    column: usize,
};

pub const Opcode = enum {
    mov,
    movd,
    nop,
    in_,
    out,
    opr,
    jmp,
    halt,
    read_d_0,
    jmp_a,
    inc,
    dec,
    load_d,
    store,
    tape_base,
    d_rewind,
    d_left,
    jz,
    jnz,
    lit,
    flag,
    var_,
    call,
};

pub const Modifier = enum {
    none,
    nop,
    movd,
};

pub const Prefix = enum {
    none,
    u,
    r,
    c,
};

pub const Operand = union(enum) {
    label: []const u8,
    number: u32,
    register_a,
};

pub const Instruction = struct {
    opcode: Opcode,
    prefix: Prefix,
    modifier: Modifier,
    operand: ?Operand,
    line: usize,
};

pub const DataEntry = struct {
    values: []const u32,
    label: ?[]const u8,
    line: usize,
};

pub const Label = struct {
    name: []const u8,
    instruction_offset: usize,
    data_offset: usize,
    line: usize,
};

pub const Section = enum { code, data };

pub const Block = struct {
    section: Section,
    instructions: std.ArrayListUnmanaged(Instruction),
    data_entries: std.ArrayListUnmanaged(DataEntry),
    labels: std.ArrayListUnmanaged(Label),

    pub fn deinit(self: *Block, allocator: std.mem.Allocator) void {
        self.instructions.deinit(allocator);
        for (self.data_entries.items) |entry| {
            if (entry.values.len > 0) allocator.free(entry.values);
        }
        self.data_entries.deinit(allocator);
        self.labels.deinit(allocator);
    }
};

pub const Program = struct {
    blocks: std.ArrayListUnmanaged(Block),

    pub fn deinit(self: *Program, allocator: std.mem.Allocator) void {
        for (self.blocks.items) |*block| {
            block.deinit(allocator);
        }
        self.blocks.deinit(allocator);
    }
};

pub const Tokenizer = struct {
    source: []const u8,
    pos: usize,
    line: usize,
    column: usize,
    pending: ?Token,

    pub fn init(source: []const u8) Tokenizer {
        return Tokenizer{ .source = source, .pos = 0, .line = 1, .column = 1, .pending = null };
    }

    pub fn nextToken(self: *Tokenizer) Token {
        if (self.pending) |p| {
            self.pending = null;
            return p;
        }
        return self.nextTokenRaw();
    }

    fn pushBack(self: *Tokenizer, t: Token) void {
        self.pending = t;
    }

    fn nextTokenRaw(self: *Tokenizer) Token {
        while (self.pos < self.source.len) {
            const c = self.source[self.pos];
            if (c == '\n') {
                self.pos += 1;
                const ret = Token{ .type = .eol, .lexeme = &[_]u8{'\n'}, .line = self.line, .column = self.column };
                self.line += 1;
                self.column = 1;
                return ret;
            }
            if (c == ' ' or c == '\t' or c == '\r') {
                self.pos += 1;
                self.column += 1;
                continue;
            }
            if (c == '/' and self.pos + 1 < self.source.len and self.source[self.pos + 1] == '/') {
                while (self.pos < self.source.len and self.source[self.pos] != '\n') {
                    self.pos += 1;
                    self.column += 1;
                }
                continue;
            }
            if (c == '/' and self.pos + 1 < self.source.len and self.source[self.pos + 1] == '*') {
                self.pos += 2;
                self.column += 2;
                while (self.pos + 1 < self.source.len) {
                    if (self.source[self.pos] == '*' and self.source[self.pos + 1] == '/') {
                        self.pos += 2;
                        self.column += 2;
                        break;
                    }
                    if (self.source[self.pos] == '\n') {
                        self.line += 1;
                        self.column = 1;
                    } else {
                        self.column += 1;
                    }
                    self.pos += 1;
                }
                continue;
            }
            return self.readToken();
        }
        return Token{ .type = .eof, .lexeme = "", .line = self.line, .column = self.column };
    }

    fn readToken(self: *Tokenizer) Token {
        const start = self.pos;
        const start_line = self.line;
        const start_col = self.column;
        const c = self.source[self.pos];

        if (c == '.') {
            self.pos += 1;
            self.column += 1;
            while (self.pos < self.source.len and isAlpha(self.source[self.pos])) {
                self.pos += 1;
                self.column += 1;
            }
            const word = self.source[start..self.pos];
            if (mem.eql(u8, word, ".CODE")) return Token{ .type = .dot_code, .lexeme = word, .line = start_line, .column = start_col };
            if (mem.eql(u8, word, ".DATA")) return Token{ .type = .dot_data, .lexeme = word, .line = start_line, .column = start_col };
            return Token{ .type = .label, .lexeme = word, .line = start_line, .column = start_col };
        }
        if (c == ':') { self.pos += 1; self.column += 1; return Token{ .type = .colon, .lexeme = self.source[start..self.pos], .line = start_line, .column = start_col }; }
        if (c == '{') { self.pos += 1; self.column += 1; return Token{ .type = .lbrace, .lexeme = self.source[start..self.pos], .line = start_line, .column = start_col }; }
        if (c == '}') { self.pos += 1; self.column += 1; return Token{ .type = .rbrace, .lexeme = self.source[start..self.pos], .line = start_line, .column = start_col }; }
        if (c == '/') { self.pos += 1; self.column += 1; return Token{ .type = .slash, .lexeme = self.source[start..self.pos], .line = start_line, .column = start_col }; }
        if (c == '?') { self.pos += 1; self.column += 1; return Token{ .type = .question, .lexeme = self.source[start..self.pos], .line = start_line, .column = start_col }; }
        if (c == '-') { self.pos += 1; self.column += 1; return Token{ .type = .minus, .lexeme = self.source[start..self.pos], .line = start_line, .column = start_col }; }
        if (c == '#') { self.pos += 1; self.column += 1; return Token{ .type = .hash, .lexeme = self.source[start..self.pos], .line = start_line, .column = start_col }; }

        if (isDigit(c)) {
            while (self.pos < self.source.len and isDigit(self.source[self.pos])) { self.pos += 1; self.column += 1; }
            return Token{ .type = .number, .lexeme = self.source[start..self.pos], .line = start_line, .column = start_col };
        }

        if (isAlpha(c) or c == '_') {
            while (self.pos < self.source.len and (isAlnum(self.source[self.pos]) or self.source[self.pos] == '_')) { self.pos += 1; self.column += 1; }
            var word = self.source[start..self.pos];

            if (word.len == 2 and word[1] == '_' and (word[0] == 'R' or word[0] == 'U' or word[0] == 'C')) {
                const prefix_tok = Token{ .type = classifyPrefix(word[0]), .lexeme = word, .line = start_line, .column = start_col };
                return prefix_tok;
            }

            if (word.len > 2 and word[1] == '_' and (word[0] == 'R' or word[0] == 'U' or word[0] == 'C')) {
                const prefix_type = classifyPrefix(word[0]);
                const prefix_tok = Token{ .type = prefix_type, .lexeme = word[0..2], .line = start_line, .column = start_col };
                const rest = word[2..];
                const rest_tok = Token{ .type = classifyKeyword(rest), .lexeme = rest, .line = start_line, .column = start_col + 2 };
                self.pushBack(rest_tok);
                return prefix_tok;
            }

            return Token{ .type = classifyKeyword(word), .lexeme = word, .line = start_line, .column = start_col };
        }

        self.pos += 1;
        self.column += 1;
        return Token{ .type = .label, .lexeme = self.source[start..self.pos], .line = start_line, .column = start_col };
    }
};

pub const Parser = struct {
    tokenizer: Tokenizer,
    current: Token,

    pub fn init(source: []const u8) Parser {
        var t = Tokenizer.init(source);
        const first = t.nextToken();
        return Parser{ .tokenizer = t, .current = first };
    }

    pub fn parse(self: *Parser, allocator: std.mem.Allocator) !Program {
        var program = Program{ .blocks = .empty };

        while (self.current.type != .eof) {
            if (self.current.type == .dot_code) {
                _ = self.advance();
                var block = Block{ .section = .code, .instructions = .empty, .data_entries = .empty, .labels = .empty };
                try self.parseCodeBody(&block, allocator);
                try program.blocks.append(allocator, block);
            } else if (self.current.type == .dot_data) {
                _ = self.advance();
                var block = Block{ .section = .data, .instructions = .empty, .data_entries = .empty, .labels = .empty };
                try self.parseDataBody(&block, allocator);
                try program.blocks.append(allocator, block);
            } else if (self.current.type == .lbrace or self.current.type == .rbrace) {
                _ = self.advance();
            } else {
                _ = self.advance();
            }
        }
        return program;
    }

    fn parseCodeBody(self: *Parser, block: *Block, allocator: std.mem.Allocator) !void {
        while (self.current.type != .eof and self.current.type != .dot_data and self.current.type != .dot_code and self.current.type != .rbrace) {
            if (self.current.type == .eol) { _ = self.advance(); continue; }
            if (self.current.type == .lbrace or self.current.type == .rbrace) { _ = self.advance(); continue; }

            if (self.looksLikeLabel()) {
                const label = self.advance();
                if (self.current.type == .colon) { _ = self.advance(); }
                try block.labels.append(allocator, .{
                    .name = label.lexeme,
                    .instruction_offset = block.instructions.items.len,
                    .data_offset = 0,
                    .line = label.line,
                });
                continue;
            }

            if (self.isOpcode()) {
                const inst = try self.parseInstruction(allocator);
                try block.instructions.append(allocator, inst);
                continue;
            }

            if (self.current.type == .number) {
                const n = std.fmt.parseInt(u32, self.current.lexeme, 10) catch 0;
                try block.instructions.append(allocator, Instruction{
                    .opcode = .lit,
                    .prefix = .none,
                    .modifier = .none,
                    .operand = Operand{ .number = n },
                    .line = self.current.line,
                });
                _ = self.advance();
                continue;
            }

            _ = self.advance();
        }
    }

    fn parseDataBody(self: *Parser, block: *Block, allocator: std.mem.Allocator) !void {
        while (self.current.type != .eof and self.current.type != .dot_code and self.current.type != .rbrace) {
            if (self.current.type == .eol) { _ = self.advance(); continue; }
            if (self.current.type == .lbrace or self.current.type == .rbrace) { _ = self.advance(); continue; }

            if (self.looksLikeLabel()) {
                const label = self.advance();
                if (self.current.type == .colon) { _ = self.advance(); }
                var data_offset: usize = 0;
                for (block.data_entries.items) |entry| data_offset += entry.values.len;
                try block.labels.append(allocator, .{
                    .name = label.lexeme,
                    .instruction_offset = block.instructions.items.len,
                    .data_offset = data_offset,
                    .line = label.line,
                });
                continue;
            }

            if (self.isOpcode()) {
                const inst = try self.parseInstruction(allocator);
                try block.instructions.append(allocator, inst);
                continue;
            }

            if (self.current.type == .number) {
                var values: std.ArrayListUnmanaged(u32) = .empty;
                while (self.current.type == .number) {
                    const n = std.fmt.parseInt(u32, self.current.lexeme, 10) catch 0;
                    try values.append(allocator, n);
                    _ = self.advance();
                }
                try block.data_entries.append(allocator, DataEntry{ .values = try values.toOwnedSlice(allocator), .label = null, .line = self.current.line });
                continue;
            }

            _ = self.advance();
        }
    }

    fn looksLikeLabel(self: *Parser) bool {
        const t = self.current.type;
        if (t == .label or t == .keyword_in or t == .keyword_out or t == .keyword_mov or t == .keyword_movd or t == .keyword_nop or t == .keyword_opr or t == .keyword_jmp or t == .keyword_halt or t == .keyword_read_d_0 or t == .keyword_jmp_a or t == .keyword_inc or t == .keyword_dec or t == .keyword_load_d or t == .keyword_store or t == .keyword_tape_base or t == .keyword_d_rewind or t == .keyword_d_left or t == .keyword_jz or t == .keyword_jnz or t == .keyword_flag or t == .keyword_var or t == .keyword_call) {
            return self.peekNextType() == .colon;
        }
        return false;
    }

    fn peekNextType(self: *Parser) TokenType {
        if (self.tokenizer.pending) |p| return p.type;
        const t = self.tokenizer.nextTokenRaw();
        self.tokenizer.pending = t;
        return t.type;
    }

    fn parseInstruction(self: *Parser, allocator: std.mem.Allocator) !Instruction {
        const prefix = self.parsePrefix();
        const opcode = self.parseOpcode();
        const modifier = self.parseModifier();
        _ = allocator;

        var operand: ?Operand = null;

        if (self.current.type == .question) {
            _ = self.advance();
            if (self.current.type == .minus) {
                _ = self.advance();
                operand = .register_a;
            }
        } else if (self.current.type == .label) {
            operand = Operand{ .label = self.current.lexeme };
            _ = self.advance();
        } else if (self.current.type == .number) {
            const n = std.fmt.parseInt(u32, self.current.lexeme, 10) catch 0;
            operand = Operand{ .number = n };
            _ = self.advance();
        }

        return Instruction{ .opcode = opcode, .prefix = prefix, .modifier = modifier, .operand = operand, .line = self.current.line };
    }

    fn parsePrefix(self: *Parser) Prefix {
        if (self.current.type == .prefix_u) { _ = self.advance(); return .u; }
        if (self.current.type == .prefix_r) { _ = self.advance(); return .r; }
        if (self.current.type == .prefix_c) { _ = self.advance(); return .c; }
        return .none;
    }

    fn parseOpcode(self: *Parser) Opcode {
        return switch (self.current.type) {
            .keyword_mov => blk: { _ = self.advance(); break :blk .mov; },
            .keyword_movd => blk: { _ = self.advance(); break :blk .movd; },
            .keyword_nop => blk: { _ = self.advance(); break :blk .nop; },
            .keyword_in => blk: { _ = self.advance(); break :blk .in_; },
            .keyword_out => blk: { _ = self.advance(); break :blk .out; },
            .keyword_opr => blk: { _ = self.advance(); break :blk .opr; },
            .keyword_jmp => blk: { _ = self.advance(); break :blk .jmp; },
            .keyword_halt => blk: { _ = self.advance(); break :blk .halt; },
            .keyword_read_d_0 => blk: { _ = self.advance(); break :blk .read_d_0; },
            .keyword_jmp_a => blk: { _ = self.advance(); break :blk .jmp_a; },
            .keyword_inc => blk: { _ = self.advance(); break :blk .inc; },
            .keyword_dec => blk: { _ = self.advance(); break :blk .dec; },
            .keyword_load_d => blk: { _ = self.advance(); break :blk .load_d; },
            .keyword_store => blk: { _ = self.advance(); break :blk .store; },
            .keyword_tape_base => blk: { _ = self.advance(); break :blk .tape_base; },
            .keyword_d_rewind => blk: { _ = self.advance(); break :blk .d_rewind; },
            .keyword_d_left => blk: { _ = self.advance(); break :blk .d_left; },
            .keyword_jz => blk: { _ = self.advance(); break :blk .jz; },
            .keyword_jnz => blk: { _ = self.advance(); break :blk .jnz; },
            .keyword_flag => blk: { _ = self.advance(); break :blk .flag; },
            .keyword_var => blk: { _ = self.advance(); break :blk .var_; },
            .keyword_call => blk: { _ = self.advance(); break :blk .call; },
            else => blk: { break :blk .nop; },
        };
    }

    fn parseModifier(self: *Parser) Modifier {
        if (self.current.type == .slash) {
            _ = self.advance();
            if (self.current.type == .keyword_nop) { _ = self.advance(); return .nop; }
            if (self.current.type == .keyword_movd) { _ = self.advance(); return .movd; }
        }
        return .none;
    }

    fn isOpcode(self: *Parser) bool {
        if (self.looksLikeLabel()) return false;
        return switch (self.current.type) {
            .keyword_mov, .keyword_movd, .keyword_nop, .keyword_in, .keyword_out, .keyword_opr, .keyword_jmp, .keyword_halt, .keyword_read_d_0, .keyword_jmp_a, .keyword_inc, .keyword_dec, .keyword_load_d, .keyword_store, .keyword_tape_base, .keyword_d_rewind, .keyword_d_left, .keyword_jz, .keyword_jnz, .keyword_flag, .keyword_var, .keyword_call => true,
            .prefix_u, .prefix_r, .prefix_c => true,
            else => false,
        };
    }

    fn advance(self: *Parser) Token {
        const prev = self.current;
        self.current = self.tokenizer.nextToken();
        return prev;
    }
};

fn classifyPrefix(c: u8) TokenType {
    return switch (c) {
        'R' => .prefix_r,
        'U' => .prefix_u,
        'C' => .prefix_c,
        else => .label,
    };
}

fn classifyKeyword(word: []const u8) TokenType {
    if (mem.eql(u8, word, "MOV")) return .keyword_mov;
    if (mem.eql(u8, word, "MovD") or mem.eql(u8, word, "MOVD")) return .keyword_movd;
    if (mem.eql(u8, word, "NOP") or mem.eql(u8, word, "Nop")) return .keyword_nop;
    if (mem.eql(u8, word, "IN") or mem.eql(u8, word, "In")) return .keyword_in;
    if (mem.eql(u8, word, "OUT") or mem.eql(u8, word, "Out")) return .keyword_out;
    if (mem.eql(u8, word, "OPR") or mem.eql(u8, word, "Opr")) return .keyword_opr;
    if (mem.eql(u8, word, "JMP") or mem.eql(u8, word, "Jmp")) return .keyword_jmp;
    if (mem.eql(u8, word, "HALT") or mem.eql(u8, word, "Halt")) return .keyword_halt;
    if (mem.eql(u8, word, "READ_D_0") or mem.eql(u8, word, "Read_d_0")) return .keyword_read_d_0;
    if (mem.eql(u8, word, "JMP_A") or mem.eql(u8, word, "Jmp_a")) return .keyword_jmp_a;
    if (mem.eql(u8, word, "INC") or mem.eql(u8, word, "Inc")) return .keyword_inc;
    if (mem.eql(u8, word, "DEC") or mem.eql(u8, word, "Dec")) return .keyword_dec;
    if (mem.eql(u8, word, "LOAD_D") or mem.eql(u8, word, "Load_d")) return .keyword_load_d;
    if (mem.eql(u8, word, "STORE") or mem.eql(u8, word, "Store")) return .keyword_store;
    if (mem.eql(u8, word, "TAPE_BASE") or mem.eql(u8, word, "Tape_base")) return .keyword_tape_base;
    if (mem.eql(u8, word, "D_REWIND") or mem.eql(u8, word, "D_rewind")) return .keyword_d_rewind;
    if (mem.eql(u8, word, "D_LEFT") or mem.eql(u8, word, "D_left")) return .keyword_d_left;
    if (mem.eql(u8, word, "JZ") or mem.eql(u8, word, "Jz")) return .keyword_jz;
    if (mem.eql(u8, word, "JNZ") or mem.eql(u8, word, "Jnz")) return .keyword_jnz;
    if (mem.eql(u8, word, "FLAG") or mem.eql(u8, word, "Flag")) return .keyword_flag;
    if (mem.eql(u8, word, "VAR") or mem.eql(u8, word, "Var")) return .keyword_var;
    if (mem.eql(u8, word, "CALL") or mem.eql(u8, word, "Call")) return .keyword_call;
    if (mem.eql(u8, word, "U_")) return .prefix_u;
    if (mem.eql(u8, word, "R_")) return .prefix_r;
    if (mem.eql(u8, word, "C_")) return .prefix_c;
    return .label;
}

fn isAlpha(c: u8) bool { return (c >= 'a' and c <= 'z') or (c >= 'A' and c <= 'Z'); }
fn isDigit(c: u8) bool { return c >= '0' and c <= '9'; }
fn isAlnum(c: u8) bool { return isAlpha(c) or isDigit(c); }

// ── A2: Opcode Table ──

pub const MalbolgeCommand = enum(u8) {
    nop = 68,
    moved = 40,
    opr = 62,
    jmp = 4,
    rot = 39,
    out = 5,
    in_ = 23,
    halt = 81,
    read_d_0 = 69,
    jmp_a = 70,
    inc = 71,
    dec = 72,
    load_d = 73,
    store = 74,
    tape_base = 75,
    d_rewind = 76,
    d_left = 77,
    jz = 78,
    jnz = 79,
};

pub const XLAT2 = "5z]&gqtyfr$(we4{WP)H-Zn,[%\\3dL+Q;>U!pJS72FhOA1CB6v^=I_0/8|jsb9m<.TVac`uY*MK'X~xDl}REokN:#?G\"i@";

pub fn hellOpcodeToCommand(opcode: Opcode, modifier: Modifier, prefix: Prefix) MalbolgeCommand {
    _ = modifier;
    if (prefix == .r) return .rot;
    return switch (opcode) {
        .movd, .mov => .moved,
        .nop => .nop,
        .in_ => .in_,
        .out => .out,
        .opr => .opr,
        .jmp => .jmp,
        .halt => .halt,
        .read_d_0 => .read_d_0,
        .jmp_a => .jmp_a,
        .inc => .inc,
        .dec => .dec,
        .load_d => .load_d,
        .store => .store,
        .tape_base => .tape_base,
        .d_rewind => .d_rewind,
        .d_left => .d_left,
        .jz => .jz,
        .jnz => .jnz,
        .lit => .nop,
        .flag => .nop,
        .var_ => .nop,
        .call => .jmp,
    };
}

pub fn commandToChar(command: MalbolgeCommand, position: usize) u8 {
    const cmd = @intFromEnum(command);
    const pos_mod = @as(u8, @intCast(@as(u32, @intCast(position % 94))));
    var ch: u8 = @intCast(((cmd + 94) -% pos_mod) % 94);
    if (ch < 33) ch += 94;
    return ch;
}

pub fn xlat2Char(c: u8) u8 {
    if (c < 33 or c > 126) return c;
    return XLAT2[c - 33];
}

pub fn isNopCommand(command: MalbolgeCommand) bool {
    return command == .nop;
}

pub fn isLoopResistant(modifier: Modifier, prefix: Prefix) bool {
    _ = modifier;
    _ = prefix;
    return false;
}

pub const OpcodeEntry = struct {
    opcode: Opcode,
    prefix: Prefix,
    modifier: Modifier,
    malbolge_command: MalbolgeCommand,
    source_char: ?u8,
};

pub fn classifyInstruction(inst: Instruction) OpcodeEntry {
    return OpcodeEntry{
        .opcode = inst.opcode,
        .prefix = inst.prefix,
        .modifier = inst.modifier,
        .malbolge_command = hellOpcodeToCommand(inst.opcode, inst.modifier, inst.prefix),
        .source_char = null,
    };
}

// ── A3: Labels and Layout ──

pub const LayoutError = error{
    DuplicateLabel,
    UnknownLabel,
    LayoutOverflow,
};

pub const ResolvedInstruction = struct {
    opcode: Opcode,
    prefix: Prefix,
    modifier: Modifier,
    operand: ?Operand,
    position: usize,
    label: ?[]const u8,
};

pub const Layout = struct {
    code_positions: std.StringHashMapUnmanaged(usize),
    data_positions: std.StringHashMapUnmanaged(usize),
    instructions: std.ArrayListUnmanaged(ResolvedInstruction),
    data_values: std.ArrayListUnmanaged(u32),
    code_size: usize,
    data_size: usize,

    pub fn deinit(self: *Layout, allocator: std.mem.Allocator) void {
        self.code_positions.deinit(allocator);
        self.data_positions.deinit(allocator);
        self.instructions.deinit(allocator);
        self.data_values.deinit(allocator);
    }
};

pub fn resolveLayout(program: *const Program, allocator: std.mem.Allocator) !Layout {
    var layout = Layout{
        .code_positions = .empty,
        .data_positions = .empty,
        .instructions = .empty,
        .data_values = .empty,
        .code_size = 0,
        .data_size = 0,
    };
    errdefer layout.deinit(allocator);

    for (program.blocks.items) |block| {
        if (block.section == .code) {
            layout.code_size += block.instructions.items.len;
        }
        if (block.section == .data) {
            for (block.data_entries.items) |entry| layout.data_size += entry.values.len;
        }
    }

    var code_cursor: usize = 0;
    for (program.blocks.items) |block| {
        if (block.section != .code) continue;
        for (block.instructions.items) |inst| {
            try layout.instructions.append(allocator, .{
                .opcode = inst.opcode,
                .prefix = inst.prefix,
                .modifier = inst.modifier,
                .operand = inst.operand,
                .position = code_cursor,
                .label = null,
            });
            code_cursor += 1;
        }
    }

    var data_cursor: usize = 0;
    for (program.blocks.items) |block| {
        if (block.section != .data) continue;
        for (block.instructions.items) |inst| {
            try layout.instructions.append(allocator, .{
                .opcode = inst.opcode,
                .prefix = inst.prefix,
                .modifier = inst.modifier,
                .operand = inst.operand,
                .position = layout.code_size + data_cursor,
                .label = null,
            });
            data_cursor += 1;
        }
        for (block.data_entries.items) |entry| {
            for (entry.values) |v| try layout.data_values.append(allocator, v);
        }
    }

    try resolveLabels(&layout, program, allocator);

    return layout;
}

pub fn resolveLabels(layout: *Layout, program: *const Program, allocator: std.mem.Allocator) !void {
    var code_base: usize = 0;
    var data_base: usize = layout.code_size;
    for (program.blocks.items) |block| {
        for (block.labels.items) |label| {
            const position = if (block.section == .code)
                code_base + label.instruction_offset
            else
                data_base + label.instruction_offset + label.data_offset;
            const target_map = if (block.section == .code) &layout.code_positions else &layout.data_positions;
            if (target_map.contains(label.name)) return error.DuplicateLabel;
            try target_map.put(allocator, label.name, position);
        }
        if (block.section == .code) code_base += block.instructions.items.len;
        if (block.section == .data) data_base += block.instructions.items.len;
    }

    for (layout.instructions.items) |*instruction| {
        if (instruction.operand) |operand| {
            if (operand == .label) {
                const found = layout.code_positions.get(operand.label) orelse
                    layout.data_positions.get(operand.label) orelse return error.UnknownLabel;
                instruction.operand = .{ .number = @intCast(found) };
                instruction.label = operand.label;
            }
        }
    }
}

pub fn layoutGetChar(layout: *const Layout, position: usize) ?u8 {
    if (position < layout.code_size) {
        return null;
    }
    const data_idx = position - layout.code_size;
    if (data_idx < layout.data_values.items.len) {
        return null;
    }
    return null;
}

// ── A4: Malbolge Emission ──

const XLAT2_INIT: [94]u8 = init: {
    var result: [94]u8 = undefined;
    for (XLAT2, 0..) |ch, i| {
        result[i] = ch;
    }
    break :init result;
};

pub const EmitError = error{
    InvalidPosition,
    OutputOverflow,
    InvalidDataValue,
    OutOfMemory,
};

pub const EmittedProgram = struct {
    chars: std.ArrayListUnmanaged(u8),
    init_len: usize,
    code_start: usize,

    pub fn deinit(self: *EmittedProgram, allocator: std.mem.Allocator) void {
        self.chars.deinit(allocator);
    }

    pub fn slice(self: *const EmittedProgram) []const u8 {
        return self.chars.items;
    }
};

pub fn emitCommandToChar(cmd: u8, position: usize) u8 {
    const pos_mod: u8 = @intCast(position % 94);
    var ch: u8 = ((cmd +% 94) -% pos_mod) % 94;
    if (ch < 33) ch += 94;
    return ch;
}

pub fn emitCharToCommand(ch: u8, position: usize) u8 {
    const pos_mod: u8 = @intCast(position % 94);
    var cmd: u8 = (ch +% pos_mod) % 94;
    if (cmd < 33) cmd += 94;
    return cmd;
}

pub fn emit(layout: *const Layout, allocator: std.mem.Allocator) EmitError!EmittedProgram {
    var result = EmittedProgram{
        .chars = .empty,
        .init_len = 0,
        .code_start = 0,
    };
    errdefer result.deinit(allocator);

    const total = layout.instructions.items.len + layout.data_size;
    if (total == 0) return result;

    for (0..total) |pos| {
        const ch = XLAT2_INIT[pos % 94];
        try result.chars.append(allocator, ch);
    }

    for (layout.instructions.items) |inst| {
        if (inst.opcode == .lit) {
            const num = switch (inst.operand orelse return error.InvalidDataValue) {
                .number => |n| n,
                else => return error.InvalidDataValue,
            };
            if (num < 33 or num > 126) return error.InvalidDataValue;
            if (inst.position < result.chars.items.len) {
                result.chars.items[inst.position] = @intCast(num);
            }
            continue;
        }
        const entry = classifyInstruction(Instruction{
            .opcode = inst.opcode,
            .prefix = inst.prefix,
            .modifier = inst.modifier,
            .operand = inst.operand,
            .line = 0,
        });
        const cmd: u8 = @intFromEnum(entry.malbolge_command);
        const ch = emitCommandToChar(cmd, inst.position);
        if (inst.position < result.chars.items.len) {
            result.chars.items[inst.position] = ch;
        }
    }

    // Literal DATA cells are part of the initial Malbolge memory image.
    // Values outside printable ASCII cannot be represented by Malbolge source
    // and must not silently remain as XLAT2 filler.
    const data_start = layout.instructions.items.len;
    for (layout.data_values.items, 0..) |value, index| {
        if (value < 33 or value > 126) return error.InvalidDataValue;
        const pos = data_start + index;
        if (pos >= result.chars.items.len) return error.OutputOverflow;
        result.chars.items[pos] = @intCast(value);
    }

    result.init_len = total;
    result.code_start = 0;

    return result;
}
