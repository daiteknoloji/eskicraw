import os
import json
from tree_sitter import Parser
from tree_sitter_languages import get_language

JS_LANGUAGE = get_language("javascript")
TS_LANGUAGE = get_language("typescript")
TSX_LANGUAGE = get_language("tsx")

parser = Parser()
parser.set_language(JS_LANGUAGE)

code = b"""
function add(a, b) {
  const sum = a + b;
  return sum;
}
"""

tree = parser.parse(code)
print(tree.root_node.sexp())


def get_language(filename):
    if filename.endswith(".js"):
        return JS_LANGUAGE
    elif filename.endswith(".ts"):
        return TS_LANGUAGE
    elif filename.endswith(".tsx"):
        return TSX_LANGUAGE
    return None

def extract_functions(code, lang):
    parser.set_language(lang)
    tree = parser.parse(bytes(code, "utf8"))
    root = tree.root_node

    functions = []

    def walk(node, parent_func=None):
        if node.type in ("function_declaration", "method_definition"):
            func_name = None
            # Normal function
            for child in node.children:
                if child.type == "identifier":
                    func_name = code[child.start_byte:child.end_byte]
            # Params
            params = []
            for child in node.children:
                if child.type == "formal_parameters":
                    params = [
                        code[p.start_byte:p.end_byte]
                        for p in child.children
                        if p.type == "identifier"
                    ]
            # Variables inside function body
            variables = []
            for child in node.children:
                if child.type == "statement_block":
                    variables.extend(find_variables(child, code))
            functions.append({
                "name": func_name,
                "params": params,
                "variables": variables
            })

        elif node.type in ("lexical_declaration", "variable_declaration"):
            # const foo = (a, b) => {}
            for child in node.children:
                if child.type == "variable_declarator":
                    name_node = child.child_by_field_name("name")
                    init_node = child.child_by_field_name("value")
                    if init_node and init_node.type in ("arrow_function", "function"):
                        func_name = code[name_node.start_byte:name_node.end_byte]
                        params = []
                        for c in init_node.children:
                            if c.type == "formal_parameters":
                                params = [
                                    code[p.start_byte:p.end_byte]
                                    for p in c.children
                                    if p.type == "identifier"
                                ]
                        variables = find_variables(init_node, code)
                        functions.append({
                            "name": func_name,
                            "params": params,
                            "variables": variables
                        })

        for child in node.children:
            walk(child, parent_func)

    def find_variables(node, code):
        vars_found = []
        if node.type in ("lexical_declaration", "variable_declaration"):
            for child in node.children:
                if child.type == "variable_declarator":
                    name_node = child.child_by_field_name("name")
                    if name_node:
                        vars_found.append(code[name_node.start_byte:name_node.end_byte])
        for child in node.children:
            vars_found.extend(find_variables(child, code))
        return vars_found

    walk(root)
    return functions

def analyze_directory(root_dir):
    result = {}

    # Expand the home directory symbol '~'
    expanded_root_dir = os.path.expanduser(root_dir)

    for dirpath, _, filenames in os.walk(expanded_root_dir):
        rel_dir = os.path.relpath(dirpath, expanded_root_dir)
        if rel_dir == ".":
            rel_dir = ""
        for filename in filenames:
            if filename.endswith((".js", ".ts", ".tsx")):
                filepath = os.path.join(dirpath, filename)
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    code = f.read()
                lang = get_language(filename)
                if lang:
                    funcs = extract_functions(code, lang)
                    rel_path = os.path.join(rel_dir, filename)
                    result[rel_path] = funcs
    return result

if __name__ == "__main__":
    # You may need to adjust the path to your project.
    SRC_DIR = "/var/www/element-web/src/"
    OUTPUT_FILE = "code_analysis_ast.json"

    try:
        analysis = analyze_directory(SRC_DIR)

        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(analysis, f, indent=2, ensure_ascii=False)

        print(f"Analysis saved to {SRC_DIR}{OUTPUT_FILE}")
    except Exception as e:
        print(f"An error occurred: {e}")
        print("Please ensure the path in `SRC_DIR` is correct and accessible.")
