import json
from pathlib import Path

p = Path(r'C:\Users\starw\Downloads\conversations.json')
with p.open(encoding='utf-8') as f:
    convs = json.load(f)

print('Total conversations:', len(convs))
print('Type:', type(convs))
print('First conversation keys:', list(convs[0].keys()))
print('First conversation ID:', convs[0].get('id'))
print('Title:', convs[0].get('title'))
print('created_at:', convs[0].get('created_at'))
print('updated_at:', convs[0].get('updated_at'))
print('current_node:', convs[0].get('current_node'))

mapping = convs[0].get('mapping', {})
print('Mapping type:', type(mapping))
print('Mapping keys sample:', list(mapping.keys())[:10])

root = mapping.get('root')
print('Root type:', type(root))
print('Root keys:', list(root.keys()) if isinstance(root, dict) else 'N/A')
print('Root parent:', root.get('parent'))
print('Root children count:', len(root.get('children', [])) if isinstance(root.get('children'), list) else root.get('children'))
msg = root.get('message')
print('Root message:', msg)
print('Root message type:', type(msg))

# Inspect node 1
node1 = mapping.get('1')
print('\nNode1 keys:', list(node1.keys()) if isinstance(node1, dict) else 'N/A')
print('Node1 parent:', node1.get('parent'))
print('Node1 children count:', len(node1.get('children', [])) if isinstance(node1.get('children'), list) else node1.get('children'))
msg1 = node1.get('message')
print('Node1 message type:', type(msg1))
if isinstance(msg1, dict):
    print('Node1 message keys:', list(msg1.keys()))
    content1 = msg1.get('content', {})
    print('Node1 content keys:', list(content1.keys()) if isinstance(content1, dict) else 'N/A')
    print('Node1 fragments count:', len(content1.get('fragments', [])) if isinstance(content1.get('fragments'), list) else 'N/A')
    author1 = msg1.get('author', {})
    print('Node1 author keys:', list(author1.keys()) if isinstance(author1, dict) else 'N/A')
    print('Node1 author role:', author1.get('role'))
    print('Node1 author name:', author1.get('name'))
    frags = content1.get('fragments', [])
    for i, frag in enumerate(frags[:3]):
        frag_type = frag.get('type')
        frag_content = frag.get('content', '')
        print('Fragment', i, ': type=', frag_type, ', content_length=', len(frag_content), sep='')
        print('    content sample:', frag_content[:200])

# Check a few more nodes for patterns
for node_id in ['2', '3', '4', '5']:
    node = mapping.get(node_id)
    if not isinstance(node, dict):
        continue
    msg = node.get('message')
    content = {}
    frags = []
    author = {}
    if isinstance(msg, dict):
        content = msg.get('content', {})
        frags = content.get('fragments', [])
        author = msg.get('author', {})
    parent = node.get('parent')
    children = node.get('children')
    children_count = len(children) if isinstance(children, list) else children
    frags_count = len(frags) if isinstance(frags, list) else 0
    role = author.get('role') if isinstance(author, dict) else 'N/A'
    name = author.get('name') if isinstance(author, dict) else 'N/A'
    print('Node', node_id, ': parent=', parent, ', children=', children_count, ', fragments=', frags_count, ', role=', role, ', name=', name, sep='')

# Check timestamps
print('\nTimestamp fields:')
for node_id in ['1', '2', '3']:
    node = mapping.get(node_id)
    if not isinstance(node, dict):
        continue
    msg = node.get('message')
    if isinstance(msg, dict):
        print('Node', node_id, 'message keys:', list(msg.keys()), sep='')
        print('Node', node_id, 'timestamp-like:', {k: msg.get(k) for k in ['created_at', 'updated_at', 'timestamp', 'create_time', 'send_time'] if k in msg}, sep='')

# Check conversation-level timestamps
conv = convs[0]
print('\nConversation timestamp-like:', {k: conv.get(k) for k in ['created_at', 'updated_at', 'inserted_at', 'create_time', 'update_time'] if k in conv})
