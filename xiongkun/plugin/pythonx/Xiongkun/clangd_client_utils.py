import difflib

def get_content_deltas(a, b):
    """ 
    inputs: `a` a list of string, without '\n'
    inputs: `b` a list of string, without '\n'
    outputs: changes satisfying the LSP protocol: https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/#textDocumentContentChangeEvent
    """
    changes = []

    def insert_before(line, new_text):
        change = {'range': {'start': {}, 'end': {}}, 'text': new_text}
        change['range']['start']['line'] = line
        change['range']['start']['character'] = 0
        change['range']['end']['line'] = line
        change['range']['end']['character'] = 0
        return change

    def delete_current(line):
        change = {'range': {'start': {}, 'end': {}}, 'text': ''}
        change['range']['start']['line'] = line
        change['range']['start']['character'] = 0
        change['range']['end']['line'] = line + 1
        change['range']['end']['character'] = 0
        return change

    linenr = 0
    for diff in difflib.ndiff(a, b):
        if diff.startswith("  "): 
            linenr += 1
        if diff.startswith("+ "): 
            changes.append(insert_before(linenr, diff[2:]+"\n"))
            linenr += 1
        if diff.startswith("- "): 
            changes.append(delete_current(linenr))

    return changes

def apply_content_deltas(current, changes):
    buffer = "\n".join(current)
    def to_idx(buffer, line, col):
        lines = buffer.split("\n")
        idx = 0
        for i in range(line):
            idx += len(lines[i]) + 1
        idx += col
        return idx

    for change in changes: 
        start_idx = to_idx(buffer, change['range']['start']['line'], change['range']['start']['character'])
        end_idx   = to_idx(buffer, change['range']['end']['line'], change['range']['end']['character'])
        buffer = buffer[:start_idx] + change['text'] + buffer[end_idx:]

    return buffer.split("\n")

