class SoftwareImage:
    """Representa um único arquivo de software (FLS)."""
    def __init__(self, part_number: str, file_path: str, sha256_hash: str, compatibility_list: list):
        [cite_start]self.part_number = part_number              # Identificador único da imagem [cite: 2]
        self.file_path = file_path                  # Onde o arquivo está armazenado
        [cite_start]self.sha256_hash = sha256_hash              # Hash para verificação de integridade [cite: 2]
        [cite_start]self.compatibility_list = compatibility_list # Lista de PNs compatíveis [cite: 2]