class Schema:
    def __init__(self):
        self.schema = []

    def add(self, label, offset, length, transform=None,
            schema=None, dtype="int", len_func=None):
        schema = { 'label': label,
                   'offset': offset,
                   'length': length,
                   'type': dtype,
                   'schema': schema,
                   'len_func': len_func,
                   'transform': transform}
        self.schema.append(schema)
