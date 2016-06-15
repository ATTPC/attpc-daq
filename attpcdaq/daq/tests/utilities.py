class FakeResponseState(object):
    def __init__(self, error_code=0, error_message='', state=1, trans=0):
        self.ErrorCode = str(error_code)
        self.ErrorMessage = str(error_message)
        self.State = str(state)
        self.Transition = str(int(trans))
