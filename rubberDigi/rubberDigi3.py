#!/usr/bin/env python3
"""
rubberDigi3 - DuckyScript 3.0 to Digispark Arduino Translator

This script converts DuckyScript 3.0 payloads into Arduino code compatible
with Digispark ATtiny85 boards using the DigiKeyboard library.

Supported DuckyScript 3.0 Features:
- Basic Commands: STRING, STRINGLN, DELAY, REM, ENTER, TAB, etc.
- Modifier Keys: GUI, ALT, CTRL, SHIFT and combinations
- Control Flow: IF, ELSE, ELSE_IF, END_IF, WHILE, END_WHILE
- Variables: VAR, DEFINE (constants)
- Functions: FUNCTION, END_FUNCTION, RETURN
- Advanced: REPEAT, DEFAULT_DELAY, HOLD, RELEASE
- Comments: REM, REM_BLOCK, END_REM

Author: Updated for DuckyScript 3.0 compatibility
"""

import argparse
import os
import re
import sys
from datetime import datetime
from shutil import copyfile
from typing import Optional, Tuple, List, Dict


# =============================================================================
# Arduino Sketch Templates
# =============================================================================

SKETCH_PREFIX = '''
#include "keymap.h"
#include "DigiKeyboard.h"

//// Default delay between keystrokes (can be modified by DEFAULT_DELAY)
#define KEYSTROKE_DELAY {default_delay}

// LED pins
#define LED_PIN_B 0  // LED on Model B
#define LED_PIN_A 1  // LED on Model A

int iterationCounter = 0;

// Forward declarations for functions
{function_declarations}

void setup() {{
  // Initialize LED pins as outputs
  pinMode(LED_PIN_B, OUTPUT);
  pinMode(LED_PIN_A, OUTPUT);
  digitalWrite(LED_PIN_B, LOW);
  digitalWrite(LED_PIN_A, LOW);
}}

void loop() {{
  DigiKeyboard.update();
  
  // Send initial empty keystroke to ensure connection
  DigiKeyboard.sendKeyStroke(0);
  
  // Initial delay before payload execution
  DigiKeyboard.delay(KEYSTROKE_DELAY);

  //START: DuckyScript 3.0 Payload (Converted by rubberDigi3)
'''

SKETCH_SUFFIX = '''
  //END: DuckyScript 3.0 Payload

  // Halt execution after payload completes
  while(1) {
    DigiKeyboard.delay(1000);
  }
}
'''

FUNCTION_TEMPLATE = '''
// DuckyScript Function: {name}
void {name}() {{
{body}
}}
'''


# =============================================================================
# Key Mappings for DuckyScript to Arduino
# =============================================================================

KEY_MAP: Dict[str, str] = {
    # Modifier keys
    "gui": "KEY_LEFT_GUI",
    "windows": "KEY_LEFT_GUI",
    "command": "KEY_LEFT_GUI",
    "super": "KEY_LEFT_GUI",
    "ctrl": "KEY_LEFTCONTROL",
    "control": "KEY_LEFTCONTROL",
    "alt": "KEY_LEFTALT",
    "option": "KEY_LEFTALT",
    "shift": "KEY_LEFTSHIFT",
    "leftcontrol": "KEY_LEFTCONTROL",
    "leftshift": "KEY_LEFTSHIFT",
    "leftalt": "KEY_LEFTALT",
    "leftgui": "KEY_LEFT_GUI",
    "rightcontrol": "KEY_RIGHTCONTROL",
    "rightshift": "KEY_RIGHTSHIFT",
    "rightalt": "KEY_RIGHTALT",
    "rightgui": "KEY_RIGHT_GUI",
    
    # Special keys
    "enter": "KEY_ENTER",
    "return": "KEY_ENTER",
    "space": "KEY_SPACEBAR",
    " ": "KEY_SPACEBAR",
    "tab": "KEY_TAB",
    "esc": "KEY_ESCAPE",
    "escape": "KEY_ESCAPE",
    "backspace": "KEY_BACKSPACE",
    "delete": "KEY_DELETE",
    "del": "KEY_DELETE",
    "insert": "KEY_INSERT",
    "home": "KEY_HOME",
    "end": "KEY_END",
    "pageup": "KEY_PAGEUP",
    "pagedown": "KEY_PAGEDOWN",
    "pause": "KEY_PAUSE",
    "break": "KEY_PAUSE",
    "capslock": "KEY_CAPS_LOCK",
    "numlock": "KEYPAD_NUMLOCK",
    "scrolllock": "KEY_SCROLL_LOCK",
    "printscreen": "KEY_PRINTSCREEN",
    "menu": "KEY_MENU",
    "app": "KEY_APPLICATION",
    "power": "KEY_POWER",
    
    # Arrow keys
    "up": "KEY_UPARROW",
    "uparrow": "KEY_UPARROW",
    "down": "KEY_DOWNARROW",
    "downarrow": "KEY_DOWNARROW",
    "left": "KEY_LEFTARROW",
    "leftarrow": "KEY_LEFTARROW",
    "right": "KEY_RIGHTARROW",
    "rightarrow": "KEY_RIGHTARROW",
    
    # Function keys
    "f1": "KEY_F1",
    "f2": "KEY_F2",
    "f3": "KEY_F3",
    "f4": "KEY_F4",
    "f5": "KEY_F5",
    "f6": "KEY_F6",
    "f7": "KEY_F7",
    "f8": "KEY_F8",
    "f9": "KEY_F9",
    "f10": "KEY_F10",
    "f11": "KEY_F11",
    "f12": "KEY_F12",
    "f13": "KEY_F13",
    "f14": "KEY_F14",
    "f15": "KEY_F15",
    "f16": "KEY_F16",
    "f17": "KEY_F17",
    "f18": "KEY_F18",
    "f19": "KEY_F19",
    "f20": "KEY_F20",
    "f21": "KEY_F21",
    "f22": "KEY_F22",
    "f23": "KEY_F23",
    "f24": "KEY_F24",
    
    # Keypad keys
    "keypad_enter": "KEYPAD_ENTER",
    "keypad_slash": "KEYPAD_FORWARDSLASH",
    "keypad_asterisk": "KEYPAD_ASTERISK",
    "keypad_minus": "KEYPAD_MINUS",
    "keypad_plus": "KEYPAD_PLUS",
    
    # Media keys
    "mute": "KEY_MUTE",
    "volumeup": "KEY_VOLUME_UP",
    "volumedown": "KEY_VOLUME_DOWN",
    
    # Locking keys
    "lockingcaps": "KEY_LOCKING_CAPS_LOCK",
    "lockingnum": "KEY_LOCKING_NUM_LOCK",
    "lockingscroll": "KEY_LOCKING_SCROLL_LOCK",
    
    # Letter keys
    "a": "KEY_A", "b": "KEY_B", "c": "KEY_C", "d": "KEY_D",
    "e": "KEY_E", "f": "KEY_F", "g": "KEY_G", "h": "KEY_H",
    "i": "KEY_I", "j": "KEY_J", "k": "KEY_K", "l": "KEY_L",
    "m": "KEY_M", "n": "KEY_N", "o": "KEY_O", "p": "KEY_P",
    "q": "KEY_Q", "r": "KEY_R", "s": "KEY_S", "t": "KEY_T",
    "u": "KEY_U", "v": "KEY_V", "w": "KEY_W", "x": "KEY_X",
    "y": "KEY_Y", "z": "KEY_Z",
    
    # Number keys
    "0": "KEY_0", "1": "KEY_1", "2": "KEY_2", "3": "KEY_3",
    "4": "KEY_4", "5": "KEY_5", "6": "KEY_6", "7": "KEY_7",
    "8": "KEY_8", "9": "KEY_9",
}

# Modifier key identifiers (used for combination detection)
MODIFIER_KEYS = {"gui", "windows", "command", "super", "ctrl", "control", 
                 "alt", "option", "shift", "leftcontrol", "leftshift", 
                 "leftalt", "leftgui", "rightcontrol", "rightshift", 
                 "rightalt", "rightgui"}

# Mapping modifiers to their Arduino modifier flags
MODIFIER_FLAGS = {
    "gui": "MOD_GUI_LEFT",
    "windows": "MOD_GUI_LEFT",
    "command": "MOD_GUI_LEFT",
    "super": "MOD_GUI_LEFT",
    "ctrl": "MOD_CONTROL_LEFT",
    "control": "MOD_CONTROL_LEFT",
    "alt": "MOD_ALT_LEFT",
    "option": "MOD_ALT_LEFT",
    "shift": "MOD_SHIFT_LEFT",
    "leftcontrol": "MOD_CONTROL_LEFT",
    "leftshift": "MOD_SHIFT_LEFT",
    "leftalt": "MOD_ALT_LEFT",
    "leftgui": "MOD_GUI_LEFT",
    "rightcontrol": "MOD_CONTROL_RIGHT",
    "rightshift": "MOD_SHIFT_RIGHT",
    "rightalt": "MOD_ALT_RIGHT",
    "rightgui": "MOD_GUI_RIGHT",
}


# =============================================================================
# DuckyScript Parser Class
# =============================================================================

class DuckyScriptParser:
    """Parser for DuckyScript 3.0 syntax."""
    
    def __init__(self, default_delay: int = 1000):
        self.default_delay = default_delay
        self.string_delay = 0  # Delay between characters in STRING
        self.last_command = ""
        self.indent_level = 1
        self.in_rem_block = False
        self.in_function = False
        self.current_function_name = ""
        self.functions: Dict[str, List[str]] = {}
        self.variables: Dict[str, str] = {}  # Variable name -> type
        self.constants: Dict[str, str] = {}  # Constant name -> value
        self.held_keys: List[str] = []
        
    def get_indent(self) -> str:
        """Return current indentation string."""
        return "  " * self.indent_level
    
    def get_key(self, key: str) -> Optional[str]:
        """
        Get Arduino key constant for a DuckyScript key.
        Returns None if key is not found.
        """
        return KEY_MAP.get(key.lower())
    
    def is_modifier(self, key: str) -> bool:
        """Check if a key is a modifier key."""
        return key.lower() in MODIFIER_KEYS
    
    def get_modifier_flag(self, key: str) -> Optional[str]:
        """Get the modifier flag for a modifier key."""
        return MODIFIER_FLAGS.get(key.lower())
    
    def escape_string(self, s: str) -> str:
        """Escape a string for use in Arduino code."""
        s = s.replace("\\", "\\\\")
        s = s.replace('"', '\\"')
        s = s.replace('\n', '\\n')
        s = s.replace('\r', '\\r')
        s = s.replace('\t', '\\t')
        return s
    
    def parse_keystroke(self, parts: List[str]) -> str:
        """
        Parse a keystroke command with potential modifiers.
        Returns Arduino code for the keystroke.
        """
        if not parts:
            return ""
        
        indent = self.get_indent()
        modifiers = []
        keys = []
        
        for part in parts:
            part_lower = part.lower()
            if self.is_modifier(part_lower):
                mod_flag = self.get_modifier_flag(part_lower)
                if mod_flag:
                    modifiers.append(mod_flag)
            else:
                key = self.get_key(part_lower)
                if key:
                    keys.append(key)
        
        if not keys and modifiers:
            # Only modifiers pressed (e.g., just "GUI")
            # Use first modifier as the key itself for compatibility
            first_mod = parts[0].lower()
            key = self.get_key(first_mod)
            if key:
                return f"{indent}DigiKeyboard.sendKeyStroke({key});"
        
        if not keys:
            return f"{indent}// Unknown key: {' '.join(parts)}"
        
        if modifiers:
            mod_str = " | ".join(modifiers)
            keys_str = ", ".join(keys)
            return f"{indent}DigiKeyboard.sendKeyStroke({keys_str}, {mod_str});"
        else:
            keys_str = ", ".join(keys)
            return f"{indent}DigiKeyboard.sendKeyStroke({keys_str});"
    
    def parse_line(self, line: str) -> str:
        """
        Parse a single line of DuckyScript.
        Returns the corresponding Arduino code.
        """
        line = line.strip()
        
        # Skip empty lines
        if not line:
            return ""
        
        # Handle REM_BLOCK toggle
        if self.in_rem_block:
            if line.upper() == "END_REM":
                self.in_rem_block = False
                return f"{self.get_indent()}*/"
            return f"{self.get_indent()} * {line}"
        
        # Split into command and arguments
        parts = line.split(None, 1)
        command = parts[0].upper()
        args = parts[1] if len(parts) > 1 else ""
        
        result = self._parse_command(command, args, line)
        
        # Store last executed command for REPEAT
        if command not in ("REM", "REM_BLOCK", "END_REM", "REPEAT"):
            self.last_command = result
        
        return result
    
    def _parse_command(self, command: str, args: str, original_line: str) -> str:
        """Parse a specific command and return Arduino code."""
        indent = self.get_indent()
        
        # =================================================================
        # Comments
        # =================================================================
        if command == "REM":
            return f"{indent}// {args}"
        
        if command == "REM_BLOCK":
            self.in_rem_block = True
            return f"{indent}/* {args}"
        
        if command == "END_REM":
            return f"{indent}*/"
        
        # =================================================================
        # Delay Commands
        # =================================================================
        if command == "DELAY":
            try:
                delay_ms = int(args)
                return f"{indent}DigiKeyboard.delay({delay_ms});"
            except ValueError:
                # Variable reference
                return f"{indent}DigiKeyboard.delay({args});"
        
        if command in ("DEFAULT_DELAY", "DEFAULTDELAY"):
            try:
                self.default_delay = int(args)
                return f"{indent}// Default delay set to {self.default_delay}ms"
            except ValueError:
                return f"{indent}// Invalid DEFAULT_DELAY value: {args}"
        
        if command == "STRINGDELAY":
            try:
                self.string_delay = int(args)
                return f"{indent}// String delay set to {self.string_delay}ms"
            except ValueError:
                return f"{indent}// Invalid STRINGDELAY value: {args}"
        
        # =================================================================
        # String Commands
        # =================================================================
        if command == "STRING":
            escaped = self.escape_string(args)
            if self.string_delay > 0:
                # Print character by character with delay
                lines = [f'{indent}{{ // STRING with delay']
                lines.append(f'{indent}  const char* str = "{escaped}";')
                lines.append(f'{indent}  while (*str) {{')
                lines.append(f'{indent}    DigiKeyboard.print(*str++);')
                lines.append(f'{indent}    DigiKeyboard.delay({self.string_delay});')
                lines.append(f'{indent}  }}')
                lines.append(f'{indent}}}')
                return '\n'.join(lines)
            return f'{indent}DigiKeyboard.print("{escaped}");'
        
        if command == "STRINGLN":
            escaped = self.escape_string(args)
            if self.string_delay > 0:
                lines = [f'{indent}{{ // STRINGLN with delay']
                lines.append(f'{indent}  const char* str = "{escaped}";')
                lines.append(f'{indent}  while (*str) {{')
                lines.append(f'{indent}    DigiKeyboard.print(*str++);')
                lines.append(f'{indent}    DigiKeyboard.delay({self.string_delay});')
                lines.append(f'{indent}  }}')
                lines.append(f'{indent}  DigiKeyboard.sendKeyStroke(KEY_ENTER);')
                lines.append(f'{indent}}}')
                return '\n'.join(lines)
            return f'{indent}DigiKeyboard.println("{escaped}");'
        
        # =================================================================
        # Repeat Command
        # =================================================================
        if command == "REPEAT":
            try:
                count = int(args)
                if self.last_command:
                    lines = [f"{indent}for (int _i = 0; _i < {count}; _i++) {{"]
                    lines.append(f"  {self.last_command}")
                    lines.append(f"{indent}}}")
                    return '\n'.join(lines)
                return f"{indent}// REPEAT: No previous command to repeat"
            except ValueError:
                return f"{indent}// Invalid REPEAT count: {args}"
        
        # =================================================================
        # Control Flow - IF/ELSE/WHILE
        # =================================================================
        if command == "IF":
            condition = self._translate_condition(args)
            result = f"{indent}if ({condition}) {{"
            self.indent_level += 1
            return result
        
        if command == "ELSE_IF" or command == "ELSE IF":
            self.indent_level -= 1
            indent = self.get_indent()
            condition = self._translate_condition(args)
            result = f"{indent}}} else if ({condition}) {{"
            self.indent_level += 1
            return result
        
        if command == "ELSE":
            self.indent_level -= 1
            indent = self.get_indent()
            result = f"{indent}}} else {{"
            self.indent_level += 1
            return result
        
        if command == "END_IF":
            self.indent_level -= 1
            indent = self.get_indent()
            return f"{indent}}}"
        
        if command == "WHILE":
            condition = self._translate_condition(args)
            result = f"{indent}while ({condition}) {{"
            self.indent_level += 1
            return result
        
        if command == "END_WHILE":
            self.indent_level -= 1
            indent = self.get_indent()
            return f"{indent}}}"
        
        # =================================================================
        # Variables and Constants
        # =================================================================
        if command == "VAR":
            # VAR $varname = value
            match = re.match(r'\$(\w+)\s*=\s*(.+)', args)
            if match:
                var_name = match.group(1)
                value = match.group(2).strip()
                # Replace variable references in the value ($var -> var)
                value = re.sub(r'\$(\w+)', r'\1', value)
                
                # Check if this is a reassignment (variable already exists)
                if var_name in self.variables:
                    return f'{indent}{var_name} = {value};'
                
                self.variables[var_name] = "int"  # Default to int
                if value.startswith('"') or value.startswith("'"):
                    self.variables[var_name] = "String"
                    return f'{indent}String {var_name} = {value};'
                elif '.' in value and not any(op in value for op in ['+', '-', '*', '/']):
                    self.variables[var_name] = "float"
                    return f'{indent}float {var_name} = {value};'
                else:
                    return f'{indent}int {var_name} = {value};'
            return f"{indent}// Invalid VAR syntax: {args}"
        
        if command == "DEFINE":
            # DEFINE #CONSTANT_NAME value
            match = re.match(r'#?(\w+)\s+(.+)', args)
            if match:
                const_name = match.group(1)
                value = match.group(2).strip()
                self.constants[const_name] = value
                return f'{indent}#define {const_name} {value}'
            return f"{indent}// Invalid DEFINE syntax: {args}"
        
        # =================================================================
        # Functions
        # =================================================================
        if command == "FUNCTION":
            func_name = args.strip().rstrip("()")
            self.in_function = True
            self.current_function_name = func_name
            self.functions[func_name] = []
            return f"{indent}// Function {func_name} defined below"
        
        if command == "END_FUNCTION":
            self.in_function = False
            func_name = self.current_function_name
            self.current_function_name = ""
            return f"{indent}// End of function {func_name}"
        
        if command == "RETURN":
            return f"{indent}return;"
        
        # Check if it's a function call (preserve original function name case)
        if command in self.functions:
            return f"{indent}{command}();"
        # Case-insensitive function lookup
        for func_name in self.functions:
            if args == "" and command.lower() == func_name.lower():
                return f"{indent}{func_name}();"
        
        # =================================================================
        # HOLD and RELEASE (Key holding)
        # =================================================================
        if command == "HOLD":
            key_parts = args.split()
            for key in key_parts:
                key_const = self.get_key(key)
                if key_const:
                    self.held_keys.append(key_const)
            # DigiKeyboard doesn't support key holding directly
            # We'll simulate by noting it for combined strokes
            return f"{indent}// HOLD {args} (Note: Digispark limited support)"
        
        if command == "RELEASE":
            if args.upper() == "ALL" or args == "":
                self.held_keys = []
                return f"{indent}DigiKeyboard.sendKeyStroke(0); // RELEASE ALL"
            else:
                key_const = self.get_key(args)
                if key_const in self.held_keys:
                    self.held_keys.remove(key_const)
                return f"{indent}// RELEASE {args}"
        
        # =================================================================
        # LED Control
        # =================================================================
        if command == "LED_ON":
            return f"{indent}digitalWrite(LED_PIN_B, HIGH); digitalWrite(LED_PIN_A, HIGH);"
        
        if command == "LED_OFF":
            return f"{indent}digitalWrite(LED_PIN_B, LOW); digitalWrite(LED_PIN_A, LOW);"
        
        if command == "LED_R" or command == "LED_G":
            # Digispark only has basic LEDs, map to available
            return f"{indent}digitalWrite(LED_PIN_B, HIGH); // LED"
        
        # =================================================================
        # Modifier Key Combinations
        # =================================================================
        if command in ("GUI", "WINDOWS", "COMMAND", "SUPER"):
            if args:
                return self.parse_keystroke([command] + args.split())
            return f"{indent}DigiKeyboard.sendKeyStroke(KEY_LEFT_GUI);"
        
        if command in ("CTRL", "CONTROL"):
            if args:
                return self.parse_keystroke([command] + args.split())
            return f"{indent}DigiKeyboard.sendKeyStroke(KEY_LEFTCONTROL);"
        
        if command in ("ALT", "OPTION"):
            if args:
                return self.parse_keystroke([command] + args.split())
            return f"{indent}DigiKeyboard.sendKeyStroke(KEY_LEFTALT);"
        
        if command == "SHIFT":
            if args:
                return self.parse_keystroke([command] + args.split())
            return f"{indent}DigiKeyboard.sendKeyStroke(KEY_LEFTSHIFT);"
        
        # Combined modifiers
        if command == "CTRL-SHIFT" or command == "CONTROL-SHIFT":
            key = self.get_key(args.split()[0]) if args else ""
            if key:
                return f"{indent}DigiKeyboard.sendKeyStroke({key}, MOD_CONTROL_LEFT | MOD_SHIFT_LEFT);"
            return f"{indent}// Invalid CTRL-SHIFT command"
        
        if command == "CTRL-ALT" or command == "CONTROL-ALT":
            key = self.get_key(args.split()[0]) if args else ""
            if key:
                return f"{indent}DigiKeyboard.sendKeyStroke({key}, MOD_CONTROL_LEFT | MOD_ALT_LEFT);"
            return f"{indent}// Invalid CTRL-ALT command"
        
        if command == "ALT-SHIFT":
            key = self.get_key(args.split()[0]) if args else ""
            if key:
                return f"{indent}DigiKeyboard.sendKeyStroke({key}, MOD_ALT_LEFT | MOD_SHIFT_LEFT);"
            return f"{indent}// Invalid ALT-SHIFT command"
        
        if command == "GUI-SHIFT" or command == "WINDOWS-SHIFT":
            key = self.get_key(args.split()[0]) if args else ""
            if key:
                return f"{indent}DigiKeyboard.sendKeyStroke({key}, MOD_GUI_LEFT | MOD_SHIFT_LEFT);"
            return f"{indent}// Invalid GUI-SHIFT command"
        
        if command == "CTRL-GUI" or command == "CONTROL-GUI":
            key = self.get_key(args.split()[0]) if args else ""
            if key:
                return f"{indent}DigiKeyboard.sendKeyStroke({key}, MOD_CONTROL_LEFT | MOD_GUI_LEFT);"
            return f"{indent}// Invalid CTRL-GUI command"
        
        if command == "ALT-GUI":
            key = self.get_key(args.split()[0]) if args else ""
            if key:
                return f"{indent}DigiKeyboard.sendKeyStroke({key}, MOD_ALT_LEFT | MOD_GUI_LEFT);"
            return f"{indent}// Invalid ALT-GUI command"
        
        # =================================================================
        # Single Key Commands
        # =================================================================
        key_const = self.get_key(command.lower())
        if key_const:
            return f"{indent}DigiKeyboard.sendKeyStroke({key_const});"
        
        # Try the whole line as a key combination
        all_parts = original_line.split()
        if len(all_parts) > 1:
            return self.parse_keystroke(all_parts)
        
        # Unknown command
        return f"{indent}// Unknown command: {original_line}"
    
    def _translate_condition(self, condition: str) -> str:
        """
        Translate DuckyScript condition to C++ condition.
        Handles variable references and comparison operators.
        """
        # Replace DuckyScript variable syntax ($var) with C++ variable
        condition = re.sub(r'\$(\w+)', r'\1', condition)
        
        # Replace string comparisons
        condition = condition.replace(" == ", " == ")
        condition = condition.replace(" != ", " != ")
        condition = condition.replace(" AND ", " && ")
        condition = condition.replace(" OR ", " || ")
        condition = condition.replace(" NOT ", " !")
        condition = condition.replace("TRUE", "true")
        condition = condition.replace("FALSE", "false")
        
        return condition


# =============================================================================
# Main Conversion Function
# =============================================================================

def convert_duckyscript(input_file: str, output_dir: str, verbose: bool = False) -> str:
    """
    Convert a DuckyScript file to Arduino code.
    
    Args:
        input_file: Path to the DuckyScript file
        output_dir: Directory for output files
        verbose: Print verbose output
    
    Returns:
        Path to the generated .ino file
    """
    parser = DuckyScriptParser()
    
    # First pass: scan for functions and default delay
    function_lines: Dict[str, List[str]] = {}
    current_function = None
    main_lines: List[str] = []
    
    with open(input_file, 'r', encoding='utf-8', errors='replace') as f:
        lines = f.readlines()
    
    # Scan for DEFAULT_DELAY at the start
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(('DEFAULT_DELAY', 'DEFAULTDELAY')):
            parts = stripped.split()
            if len(parts) > 1:
                try:
                    parser.default_delay = int(parts[1])
                except ValueError:
                    pass
            break
        if stripped and not stripped.startswith('REM'):
            break
    
    # Two-pass processing for functions
    in_function = False
    
    for line in lines:
        stripped = line.strip()
        
        if stripped.upper().startswith('FUNCTION '):
            func_name = stripped[9:].strip().rstrip('()')
            current_function = func_name
            function_lines[func_name] = []
            in_function = True
            continue
        
        if stripped.upper() == 'END_FUNCTION':
            current_function = None
            in_function = False
            continue
        
        if in_function and current_function:
            function_lines[current_function].append(stripped)
        else:
            main_lines.append(stripped)
    
    # Store functions in parser
    parser.functions = {name: [] for name in function_lines.keys()}
    
    # Generate function declarations
    func_declarations = []
    for func_name in function_lines.keys():
        func_declarations.append(f"void {func_name}();")
    
    # Generate main code
    main_code_lines: List[str] = []
    for line in main_lines:
        if line:
            result = parser.parse_line(line)
            if result:
                main_code_lines.append(result)
    
    # Generate function implementations
    function_implementations: List[str] = []
    for func_name, func_body_lines in function_lines.items():
        func_parser = DuckyScriptParser(parser.default_delay)
        func_parser.functions = parser.functions
        func_code: List[str] = []
        for line in func_body_lines:
            if line:
                result = func_parser.parse_line(line)
                if result:
                    func_code.append(f"  {result}")
        
        func_impl = FUNCTION_TEMPLATE.format(
            name=func_name,
            body='\n'.join(func_code) if func_code else "  // Empty function"
        )
        function_implementations.append(func_impl)
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Build final sketch
    sketch_prefix = SKETCH_PREFIX.format(
        default_delay=parser.default_delay,
        function_declarations='\n'.join(func_declarations) if func_declarations else "// No functions defined"
    )
    
    output = []
    output.append(f"// Converted from DuckyScript 3.0 at {datetime.now()}")
    output.append(f"// Source: {os.path.basename(input_file)}")
    output.append(f"// Generated by rubberDigi3")
    output.append(sketch_prefix)
    output.extend(main_code_lines)
    output.append(SKETCH_SUFFIX)
    
    # Add function implementations after loop()
    if function_implementations:
        output.append("\n// ========== Function Implementations ==========\n")
        output.extend(function_implementations)
    
    # Write output file
    output_path = os.path.join(output_dir, 'output.ino')
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(output))
    
    # Copy keymap.h to output directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    keymap_src = os.path.join(script_dir, 'keymap.h')
    keymap_dest = os.path.join(output_dir, 'keymap.h')
    
    if os.path.exists(keymap_src):
        copyfile(keymap_src, keymap_dest)
        if verbose:
            print(f"Copied keymap.h to {keymap_dest}")
    else:
        # Try current working directory
        keymap_src = os.path.join(os.getcwd(), 'keymap.h')
        if os.path.exists(keymap_src):
            copyfile(keymap_src, keymap_dest)
            if verbose:
                print(f"Copied keymap.h to {keymap_dest}")
        else:
            print(f"Warning: keymap.h not found. Please copy it manually to {output_dir}")
    
    if verbose:
        print(f"Generated: {output_path}")
        print(f"Default delay: {parser.default_delay}ms")
        if function_lines:
            print(f"Functions defined: {', '.join(function_lines.keys())}")
    
    return output_path


# =============================================================================
# CLI Entry Point
# =============================================================================

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description='Convert DuckyScript 3.0 to Digispark Arduino code.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python rubberDigi3.py payload.txt
  python rubberDigi3.py payload.txt -o my_output
  python rubberDigi3.py payload.txt -v

Supported DuckyScript 3.0 commands:
  STRING, STRINGLN, DELAY, REM, REM_BLOCK, END_REM
  ENTER, TAB, ESC, BACKSPACE, DELETE, INSERT, HOME, END
  PAGEUP, PAGEDOWN, UPARROW, DOWNARROW, LEFTARROW, RIGHTARROW
  GUI/WINDOWS, CTRL/CONTROL, ALT, SHIFT
  CTRL-SHIFT, CTRL-ALT, ALT-SHIFT, GUI-SHIFT
  IF, ELSE, ELSE_IF, END_IF, WHILE, END_WHILE
  VAR, DEFINE, FUNCTION, END_FUNCTION, RETURN
  REPEAT, DEFAULT_DELAY, HOLD, RELEASE
  LED_ON, LED_OFF, F1-F24
        """
    )
    
    parser.add_argument(
        'duckyscript',
        help='Path to the DuckyScript file to convert'
    )
    
    parser.add_argument(
        '-o', '--output',
        default='output',
        help='Output directory (default: ./output)'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    
    args = parser.parse_args()
    
    # Validate input file
    if not os.path.exists(args.duckyscript):
        print(f"Error: Input file not found: {args.duckyscript}")
        sys.exit(1)
    
    # Convert
    print(f"Input File: {args.duckyscript}")
    
    output_dir = args.output
    if not os.path.isabs(output_dir):
        output_dir = os.path.join(os.getcwd(), output_dir)
    
    print(f"Output Directory: {output_dir}")
    
    try:
        output_path = convert_duckyscript(
            args.duckyscript,
            output_dir,
            verbose=args.verbose
        )
        print(f"Success! Arduino sketch generated: {output_path}")
    except Exception as e:
        print(f"Error during conversion: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()