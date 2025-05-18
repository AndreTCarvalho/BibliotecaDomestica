// /seu_projeto_biblioteca/static/js/main.js

document.addEventListener('DOMContentLoaded', () => {
    // --- Lógica para a Câmera (Gemini) na página de registro ---
    const toggleCameraGeminiBtn = document.getElementById('toggle-camera-gemini-btn');
    const cameraSectionGemini = document.getElementById('camera-section-gemini');
    const videoElementGemini = document.getElementById('camera-feed-gemini');
    const canvasElementGemini = document.getElementById('snapshot-canvas-gemini');
    const takeSnapshotGeminiBtn = document.getElementById('take-snapshot-gemini-btn');
    const snapshotPreviewGemini = document.getElementById('snapshot-preview-gemini');
    const geminiStatusMsg = document.getElementById('gemini-status-message');
    let geminiCameraStream; // Para armazenar o stream da câmera

    if (toggleCameraGeminiBtn) {
        toggleCameraGeminiBtn.addEventListener('click', async () => {
            if (cameraSectionGemini.style.display === 'none' || cameraSectionGemini.style.display === '') {
                // Tenta abrir a câmera
                try {
                    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
                        alert('Seu navegador não suporta acesso à câmera. Tente um navegador mais moderno.');
                        if(geminiStatusMsg) geminiStatusMsg.textContent = 'Acesso à câmera não suportado.';
                        return;
                    }
                    // Pede permissão e inicia a câmera (preferencialmente a traseira)
                    geminiCameraStream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } });
                    videoElementGemini.srcObject = geminiCameraStream;
                    videoElementGemini.play(); // Garante que o vídeo comece
                    cameraSectionGemini.style.display = 'block';
                    toggleCameraGeminiBtn.innerHTML = '<img src="/static/icons/camera-off.svg" alt="" class="icon"> Fechar Câmera'; // Mude o texto/ícone do botão
                    if(geminiStatusMsg) geminiStatusMsg.textContent = 'Câmera ativa. Aponte para a capa do livro.';
                } catch (err) {
                    console.error("Erro ao acessar a câmera (Gemini): ", err);
                    alert('Erro ao acessar a câmera. Verifique as permissões do navegador para este site.');
                    if(geminiStatusMsg) geminiStatusMsg.textContent = `Erro ao acessar câmera: ${err.name}. Verifique as permissões.`;
                }
            } else {
                // Fecha a câmera
                if (geminiCameraStream) {
                    geminiCameraStream.getTracks().forEach(track => track.stop());
                }
                videoElementGemini.srcObject = null;
                cameraSectionGemini.style.display = 'none';
                snapshotPreviewGemini.style.display = 'none'; // Esconde a prévia
                snapshotPreviewGemini.src = '#'; // Limpa a prévia
                toggleCameraGeminiBtn.innerHTML = '<img src="/static/icons/camera.svg" alt="" class="icon"> Acessar Câmera para buscar Infos (Gemini)';
                if(geminiStatusMsg) geminiStatusMsg.textContent = '';
            }
        });
    }

    if (takeSnapshotGeminiBtn) {
        takeSnapshotGeminiBtn.addEventListener('click', () => {
            if (!geminiCameraStream || !videoElementGemini.srcObject || videoElementGemini.paused || videoElementGemini.ended || videoElementGemini.readyState < videoElementGemini.HAVE_CURRENT_DATA) {
                alert("A câmera não está ativa ou pronta. Por favor, ative a câmera primeiro.");
                if(geminiStatusMsg) geminiStatusMsg.textContent = 'Câmera não está pronta. Ative-a.';
                return;
            }
            if(geminiStatusMsg) geminiStatusMsg.textContent = 'Capturando foto...';

            // Define as dimensões do canvas para as dimensões reais do vídeo
            canvasElementGemini.width = videoElementGemini.videoWidth;
            canvasElementGemini.height = videoElementGemini.videoHeight;

            const context = canvasElementGemini.getContext('2d');
            context.drawImage(videoElementGemini, 0, 0, canvasElementGemini.width, canvasElementGemini.height);

            // Mostra a prévia da foto tirada
            const imageDataUrl = canvasElementGemini.toDataURL('image/jpeg', 0.9); // Qualidade 0.9
            snapshotPreviewGemini.src = imageDataUrl;
            snapshotPreviewGemini.style.display = 'block';

            // Converte o Data URL para Blob para enviar como um arquivo via FormData
            canvasElementGemini.toBlob(async (blob) => {
                if (!blob) {
                    if(geminiStatusMsg) geminiStatusMsg.textContent = 'Erro ao criar dados da imagem para envio.';
                    console.error('Erro ao converter canvas para Blob.');
                    return;
                }

                const formData = new FormData();
                const fileName = `gemini_snapshot_${Date.now()}.jpg`; // Nome de arquivo para o blob
                formData.append('image_data', blob, fileName);

                if(geminiStatusMsg) geminiStatusMsg.textContent = 'Enviando imagem para análise... Aguarde.';

                try {
                    const response = await fetch('/analyze_cover_via_gemini', {
                        method: 'POST',
                        body: formData
                        // O 'Content-Type': 'multipart/form-data' é definido automaticamente pelo browser com FormData
                    });

                    if (response.ok) {
                        const data = await response.json();

                        if (data.error) {
                             if(geminiStatusMsg) geminiStatusMsg.textContent = `Erro da API: ${data.error}`;
                        } else {

                            console.log(data)
                            // Preenche os campos do formulário com os dados recebidos
                            document.getElementById('title').value = data.title || '';
                            document.getElementById('author').value = data.author || '';
                            document.getElementById('language').value = data.language || '';
                            document.getElementById('review').value = data.review || '';
                            if(geminiStatusMsg) geminiStatusMsg.textContent = 'Informações preenchidas pela IA! Verifique e edite se necessário.';

                            // Opcional: Fechar a câmera após a análise bem-sucedida
                            if (geminiCameraStream) {
                                geminiCameraStream.getTracks().forEach(track => track.stop());
                            }
                            videoElementGemini.srcObject = null;
                            cameraSectionGemini.style.display = 'none';
                            toggleCameraGeminiBtn.innerHTML = '<img src="/static/icons/camera.svg" alt="" class="icon"> Acessar Câmera para buscar Infos (Gemini)';
                        }
                    } else {
                        const errorText = await response.text(); // Pega mais detalhes do erro do servidor
                        if(geminiStatusMsg) geminiStatusMsg.textContent = `Erro no servidor: ${response.status}. Detalhes: ${errorText}`;
                        console.error("Erro do servidor ao analisar capa:", response.status, errorText);
                    }
                } catch (error) {
                    if(geminiStatusMsg) geminiStatusMsg.textContent = 'Falha na comunicação com o servidor para análise da imagem.';
                    console.error('Erro ao enviar imagem para análise com Gemini:', error);
                }
            }, 'image/jpeg', 0.9); // Tipo MIME e qualidade para o Blob
        });
    }

    // --- Lógica para preview de imagem no upload de arquivo (genérico) ---
    // Esta função pode ser usada para os inputs de arquivo de capa nas páginas de registro e edição.
    function setupImagePreview(fileInputElementId, previewElementId) {
        const fileInput = document.getElementById(fileInputElementId);
        const previewElement = document.getElementById(previewElementId);

        if (fileInput && previewElement) {
            fileInput.addEventListener('change', function(event) {
                const file = event.target.files[0];
                if (file) {
                    const reader = new FileReader();
                    reader.onload = function(e) {
                        previewElement.src = e.target.result;
                        previewElement.style.display = 'block';
                    }
                    reader.readAsDataURL(file);
                } else {
                    previewElement.src = '#'; // Limpa a prévia
                    previewElement.style.display = 'none'; // Esconde a prévia
                }
            });
        }
    }

    // Aplica a função de preview para a página de registro (se os elementos existirem)
    setupImagePreview('cover_image_file', 'cover-upload-preview');

    // Aplica a função de preview para a página de edição (se os elementos existirem)
    setupImagePreview('cover_image_file_edit', 'new-cover-preview-edit');

}); // Fim do DOMContentLoaded