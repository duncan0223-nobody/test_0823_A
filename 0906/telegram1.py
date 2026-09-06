class Message:
    def reply_text(self,text:str)->str:
        return text
        
class Update:
    def __init__(self):
        self.message = Message()
    