from gse.backend.models.software_image import SoftwareImage

class ImageService:
    """Gerencia todas as operações relacionadas às imagens de software."""
    def import_image(self, external_path: str) -> SoftwareImage:
        """Importa uma imagem, verifica sua integridade e a move para a pasta 'data'."""
        if not self._verify_sha256(external_path):
            # Lança uma exceção de falha de integridade
            raise ValueError("Falha na verificação de integridade do arquivo.")
        # Lógica para mover o arquivo, ler o PN e a lista de compatibilidade
        # ...
        return SoftwareImage(...)

    def list_images(self) -> list[SoftwareImage]:
        """Retorna uma lista de todas as imagens de software gerenciadas pelo GSE."""
        # Lógica para ler a pasta 'data' e criar os objetos SoftwareImage
        # ...
        return []

    def _verify_sha256(self, file_path: str) -> bool:
        """Função privada para calcular e verificar o hash SHA-256 de um arquivo."""
        # ...
        return True