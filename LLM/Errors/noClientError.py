
class NoClientError(Exception):
    def __init__(self, message="No client provided. Please provide a valid client.", error_code=404):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
