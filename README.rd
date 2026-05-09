# OTBM to OTMM Converter (OTClientV8 8.60)

Este script foi desenvolvido para resolver o erro de **'bad allocation'** ou crashes no **OTClientV8** ao tentar carregar mapas muito grandes ou com muitas customizações via `g_map.loadOtbm`. 

Em vez de forçar o client a processar o binário do mapa em tempo de execução (o que consome muita RAM e causa o crash), este script converte o arquivo `.otbm` diretamente para `.otmm` (formato de minimap pré-processado), permitindo que o minimap completo apareça instantaneamente sem pesar no client.

Funcionalidades
- Leitura de arquivos `Tibia.dat` (Versão 8.60) para extração de cores reais.
- Parsing de `items.otb` para mapeamento de Client ID e Server ID.
- Leitura completa de árvore binária de arquivos `.otbm`.
- Suporte a Zonas de Proteção, Casas e No-PVP (correção de renderização preta).
- Geração de arquivo `minimap.otmm` compatível com OTCv8.

Pré-requisitos
- Python 3.x instalado.
- Os arquivos do seu servidor na mesma pasta do script:
  - `Tibia.dat`
  - `items.otb`
  - `mapadois.otbm` (ou mude o nome no código)

Solução de Problemas (Importante!)

Caso o minimap gerado apresente falhas ou o mapa "quebre" na renderização, isso pode acontecer porque a source (SRC) do seu servidor possui uma lógica de IDs diferente da padrão utilizada neste script.

Se isso ocorrer, verifique as seguintes linhas no arquivo `main.py` (linhas 52, 67 e 80):
"if 20000 < gid < 20100: gid -= 20000"