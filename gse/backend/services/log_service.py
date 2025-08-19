class LogService:
    """Serviço centralizado para registro de eventos (logs)."""
    def log_info(self, message: str):
        """Registra uma mensagem informativa."""
        # Lógica para escrever no arquivo de log com data e hora
        print(f"[INFO] {message}")

    def log_error(self, message: str):
        """Registra uma mensagem de erro."""
        print(f"[ERROR] {message}")