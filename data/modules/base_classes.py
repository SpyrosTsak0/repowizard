
class BaseClasses:

    class Repository:
        def __init__(self, name, ID, auto_delete_head):
           self.name = name
           self.ID = ID
           self.auto_delete_head = auto_delete_head
    