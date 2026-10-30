# Game Screenshot Translator

Tradutor de screenshots de jogos, de inglês para português brasileiro, feito em Python.

> **Status: fase inicial de desenvolvimento (protótipo experimental).** As funcionalidades e a configuração ainda podem mudar. O reconhecimento de texto e a tradução podem apresentar erros, e a compatibilidade precisa ser avaliada em cada jogo.

O objetivo é ajudar na leitura de diálogos, descrições de itens e menus de jogos sem tradução para português. O programa acompanha uma pasta de screenshots, extrai o texto com OCR (reconhecimento de texto em imagens) e mostra o original e a tradução em uma janela separada, que pode ficar em um segundo monitor.

## Em quais tipos de jogos pode ser usado?

O uso faz mais sentido em jogos em que você consegue parar para ler e tirar uma captura de tela:

| Tipo de jogo | Possível uso |
| --- | --- |
| RPGs por turnos e RPGs com pausa | Ler diálogos, missões, descrições de itens e habilidades. |
| Visual novels e jogos narrativos | Traduzir falas e escolhas que permanecem na tela até o jogador avançar. |
| Aventuras e point-and-click | Entender conversas, pistas e descrições de objetos. |
| Estratégia e gerenciamento com pausa ou turnos | Consultar tutoriais, eventos e descrições de menus. |
| Outros jogos com textos estáticos | Ler inventários, livros, cartas e telas de ajuda. |

Esses são cenários de uso sugeridos com base no funcionamento do programa, não uma lista de jogos testados. Ainda não há uma lista de títulos com compatibilidade validada neste repositório.

Jogos de ação rápida, partidas competitivas e legendas que desaparecem rapidamente tendem a ser menos adequados: é necessário salvar um screenshot e aguardar o OCR e a tradução. Não há captura contínua da tela nem tradução sobreposta ao jogo.

## Como funciona

1. Você tira um screenshot e ele é salvo na pasta configurada.
2. O programa detecta a nova imagem e tenta ler o texto em inglês com Tesseract OCR.
3. O texto reconhecido é enviado ao MyMemory para tradução em português brasileiro.
4. A janela mostra o texto original e a tradução lado a lado.

A ferramenta trabalha com arquivos de imagem: não lê a memória do jogo, não injeta código e não modifica seus arquivos.

## O que já está implementado

- Monitoramento de uma pasta de screenshots, sem incluir subpastas.
- Leitura de imagens PNG, JPG, JPEG, WebP e BMP.
- Pré-processamento de imagens para tentar melhorar o reconhecimento do texto.
- Tradução de inglês para português brasileiro pelo MyMemory.
- Janela com texto original e tradução, posição por monitor e opção de ficar sempre visível.
- Opção de apagar a imagem após o processamento e filtro por data de modificação para ignorar imagens anteriores à abertura do programa.

## Limitações atuais

- A instalação descrita é voltada ao Windows; outros sistemas ainda precisam de validação.
- Fontes estilizadas, texto pequeno, fundos complexos e vários blocos de texto podem prejudicar o OCR. O programa tenta ler a imagem inteira e ainda não oferece seleção de uma região.
- A tradução depende de internet, da disponibilidade e dos limites do MyMemory. Nomes próprios e termos específicos dos jogos podem ser traduzidos incorretamente.
- O texto extraído é enviado a um serviço externo. Considere isso ao usar capturas com mensagens privadas ou outras informações pessoais.
- O fluxo de tradução está fixo em inglês → português brasileiro. Alterar apenas o idioma do OCR não muda os idiomas da tradução.
- A janela exibe o resultado mais recente, sem histórico persistente.
- Ainda não há instalador, executável distribuído ou interface para editar as configurações.

## Instalação e primeiro uso (Windows)

Você precisa de Python 3.10 ou superior, Tesseract OCR com o idioma inglês instalado e conexão com a internet para traduzir.

1. Instale o [Python](https://www.python.org/downloads/) e habilite sua inclusão no PATH.
2. Instale o Tesseract OCR seguindo as orientações para Windows do projeto [UB Mannheim](https://github.com/UB-Mannheim/tesseract/wiki). Inclua o idioma inglês (`eng`).
3. Baixe este repositório, extraia os arquivos se necessário e abra o terminal na pasta do projeto.
4. Instale as dependências:

   ```powershell
   py -m pip install -r requirements.txt
   ```

5. Se ainda não tiver um `config.json`, crie sua configuração local a partir do exemplo:

   ```powershell
   Copy-Item config.example.json config.json
   ```

6. Abra o `config.json` e ajuste:

   - `screenshots_folder`: caminho de uma pasta existente onde os screenshots serão salvos.
   - `tesseract_cmd`: caminho do executável do Tesseract no seu computador.
   - `delete_after_processing`: use `false` nos primeiros testes para preservar as imagens.
   - `monitor_number`: use `1` se quiser abrir a janela no primeiro monitor enumerado pelo Windows.

   Em caminhos no JSON, use barras `/` como no exemplo ou escape as barras invertidas com `\\`.

   **Atenção:** tanto o exemplo quanto a configuração gerada pelo programa usam `delete_after_processing: true`. Nesse modo, cada imagem é apagada permanentemente após o OCR e a tradução concluírem com sucesso. Altere para `false` antes de executar se quiser guardar os screenshots.

7. Execute:

   ```powershell
   py app.py
   ```

8. Com o programa aberto, tire um novo screenshot no jogo e salve-o na pasta configurada. Aguarde o resultado na janela do tradutor. Para encerrar, feche a janela.

Se o programa for executado sem `config.json`, ele cria um arquivo com os valores padrão e encerra para que você o edite antes de abrir novamente. A pasta de screenshots deve existir; o programa não a cria.

## Configuração

O arquivo [config.example.json](config.example.json) contém um modelo sem caminhos pessoais. O `config.json` é local e está incluído no `.gitignore`.

| Opção | Comportamento atual |
| --- | --- |
| `screenshots_folder` | Pasta monitorada. Precisa ser ajustada para seu computador. |
| `tesseract_cmd` | Caminho do executável `tesseract.exe`. |
| `ocr_language` | Idioma do OCR; padrão `eng`. Não altera o par de idiomas da tradução. |
| `monitor_number` | Índice do monitor na enumeração do Windows, começando em `1`; padrão `2`. Se o índice não existir, usa o primeiro disponível. |
| `window_width` / `window_height` | Dimensões da janela em pixels; padrão `720` × `520`. |
| `always_on_top` | Mantém a janela acima de outras janelas; padrão `true`. A visibilidade em tela cheia depende do modo do jogo. |
| `preprocess_image` | Ajusta contraste, tamanho e nitidez antes do OCR; padrão `true`. |
| `minimum_text_length` | Quantidade mínima de caracteres reconhecidos para tentar traduzir; padrão `2`. |
| `translation_provider` | Campo presente na configuração, mas sem seleção de provedores implementada. O código usa MyMemory. |
| `delete_after_processing` | Apaga a imagem após OCR e tradução bem-sucedidos; padrão `true`. Use `false` para preservar arquivos. |
| `only_process_files_created_after_start` | Ignora imagens cuja data de modificação seja anterior à abertura do programa; padrão `true`. Não processa automaticamente os arquivos já existentes na pasta. |

## Solução de problemas

- **Tesseract não encontrado:** confira a instalação e o caminho em `tesseract_cmd`.
- **Pasta inválida:** confira se `screenshots_folder` aponta para uma pasta existente e se o JSON está válido.
- **Screenshot não aparece:** salve uma imagem nova diretamente na pasta monitorada depois de abrir o tradutor. Subpastas não são acompanhadas.
- **Texto reconhecido incorretamente:** tente uma captura com texto maior e mais nítido. Textos misturados com muitos elementos visuais podem exigir um recorte antes de salvar a imagem na pasta monitorada.
- **Tradução falha ou demora:** confira a conexão e tente novamente mais tarde; o serviço externo pode estar indisponível ou limitar solicitações.

## Possíveis próximos passos

Ideias para evolução, ainda sem prazo ou compromisso de implementação:

- Validar o funcionamento em jogos específicos e documentar os resultados.
- Permitir selecionar a região da imagem que contém o texto.
- Oferecer edição de configurações pela interface.
- Adicionar histórico de traduções e suporte a outros idiomas e provedores.
- Simplificar a instalação e a distribuição para Windows.

## Contribuições

O projeto está aberto a relatos de problemas e sugestões. Ao abrir uma issue, informe a versão do Windows e do Python, o jogo e a situação em que o erro ocorreu. Se possível, inclua o erro exibido e uma captura de exemplo sem dados pessoais. Não envie seu `config.json` com caminhos locais.
