import os

def tem_permissao_escrita(diretorio):
    """Verifica se o processo atual tem permissão de escrita no diretório."""
    if not os.path.exists(diretorio):
        return False  # Diretório não existe
    if not os.path.isdir(diretorio):
        return False  # Não é um diretório
    try:
        # Tenta criar um arquivo temporário no diretório
        temp_file = os.path.join(diretorio, "temp_test_file.txt")
        with open(temp_file, "w"):
            pass
        os.remove(temp_file)  # Limpa o arquivo temporário
        return True
    except OSError:
        return False  # Não tem permissão de escrita

# Exemplo de uso
diretorio_para_verificar = "..\instance"  # Substitua pelo diretório que você quer verificar
if tem_permissao_escrita(diretorio_para_verificar):
    print(f"O processo tem permissão de escrita no diretório {diretorio_para_verificar}")
else:
    print(f"O processo não tem permissão de escrita no diretório {diretorio_para_verificar}")