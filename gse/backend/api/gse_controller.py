# Importa todos os services
from gse.backend.services.auth_service import AuthService
from gse.backend.services.image_service import ImageService
from gse.backend.services.comm_service import CommunicationService
from gse.backend.services.log_service import LogService

class GseController:
    """Ponto de entrada único para o frontend. Orquestra as chamadas para os serviços."""
    def __init__(self):
        self.auth_service = AuthService()
        self.image_service = ImageService()
        self.comm_service = CommunicationService()
        self.log_service = LogService()

    def login(self, username: str, password: str) -> bool:
        """Tenta autenticar um usuário."""
        self.log_service.log_info(f"Tentativa de login para o usuário: {username}")
        # Lógica para chamar o auth_service e registrar falhas no log
        is_valid = self.auth_service.validate_credentials(username, password)
        if not is_valid:
            self.log_service.log_error(f"Falha no login para o usuário: {username}")
        return is_valid

    def get_software_images_list(self) -> list[dict]:
        """Retorna os dados das imagens para o frontend exibir."""
        images = self.image_service.list_images()
        # Converte a lista de objetos para um formato simples que o frontend possa usar
        return [{"part_number": img.part_number, ...} for img in images]

    def start_upload_process(self, part_number: str):
        """Inicia todo o fluxo de carregamento de uma imagem."""
        self.log_service.log_info(f"Iniciando processo de carregamento para o PN: {part_number}")
        # Lógica para obter a imagem, chamar o serviço de comunicação, etc.
        # ...