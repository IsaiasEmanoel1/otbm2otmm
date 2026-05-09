import struct

# Constantes globais do OpenTibia
NODE_START = 0xFE
NODE_END = 0xFF
NODE_ESCAPE = 0xFD

class NodeReader:
    def __init__(self, data):
        self.data = data
        self.pos = 0

    def get_byte(self):
        if self.pos >= len(self.data):
            return None
        b = self.data[self.pos]
        self.pos += 1
        return b

    def get_next_node(self):
        byte = self.get_byte()
        if byte is None:
            return None
        
        if byte == NODE_START:
            return self.parse_node()
        return None

    def parse_node(self):
        node_type = self.get_byte()
        props_data = bytearray()
        children = []
        
        while self.pos < len(self.data):
            byte = self.get_byte()
            
            if byte == NODE_END:
                # Fim do nó atual
                break
            elif byte == NODE_START:
                # Achou um nó filho (uma sub-pasta)
                child_node = self.parse_node()
                if child_node:
                    children.append(child_node)
            elif byte == NODE_ESCAPE:
                # Achou o byte de escape, pega o próximo byte puro
                escaped_byte = self.get_byte()
                if escaped_byte is not None:
                    props_data.append(escaped_byte)
            else:
                props_data.append(byte)
                
        return {'type': node_type, 'data': props_data, 'children': children}