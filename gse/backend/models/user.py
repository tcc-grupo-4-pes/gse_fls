class User:
    """Representa um usuário autorizado do sistema."""
    def __init__(self, username: str, hashed_password: str):
        self.username = username
        self.hashed_password = hashed_password