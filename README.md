# KML Placemark Renamer Tool

Esta é uma ferramenta gráfica construída em **Python + PyQt6** desenvolvida para analisar, filtrar e renomear dinamicamente metadados de marcadores (Placemarks) dentro de arquivos Google Earth KML. O foco principal do sistema é varrer tags internas de informações (`<Data>`, `<value>`) e validar numenclaturas específicas através de lógicas robustas de extração de padrões da engenharia (DAN e Altura de postes).

A aplicação conta com uma esteira de QA sólida, mantendo **100% de Test Coverage** (Cobertura de Testes) automatizada em validações unitárias, fluxo e simulação de corrpção de armazenamento.

---

## 🚀 Principais Features

### 1. Descoberta Automática de Modelos de Dados
O sistema lê um arquivo KML e infere assinaturas de chave-valor baseadas nas tags `<ExtendedData>` presentes. Modelos de marcadores contendo as mesmas propriedades (Ex: "pictures, notes, altura") são agrupados visualmente para o usuário configurar políticas de renomeação em massa exclusivas por modelo.

### 2. Regex Inteligente e Extração Estrutural
Toda extração textual passa por um sanitizador responsável por ignorar textos inúteis ou lixo HTML contido nas descrições de postes. Ele então resgata chaves e números usando validação baseada em intervalos físicos estritos:
- **ALTURA:** Extensões aceitas entre `6` a `14`.
- **DAN (Disposição/Distância/Tag):** Extensões aceitas entre `100` e `2000`.

### 3. Ordem Fixa Forçada
O script processa campos unificados ou multiselecionados unindo todos os números e forçando a padronização do nome resultante do marcador.
A lógica organiza para que **independentemente da ordem na qual eles apareceram descritos no arquivo de entrada**, a saída gerada seja invariavelmente:
👉 `DAN-Altura`

`Exemplo:` 
*Entrada mal formatada:* `<value>P-11/300</value>`
*Saída validada:* `300-11`

### 4. Pastas Nativas no KML e Filtragem Qualitativa
A ferramenta é inteligente a ponto de preservar integralmente a arquitetura visual, links, CSS e ícones de Google Earth presentes na sua importação original. 
Após renomear os Placemarks aplicáveis, a aplicação *poda* a árvore KML final em duas sub-pastas nativas do Google Earth (`<Folder>`):
- 📁 **Aprovados:** Lista os marcadores onde ambos `DAN` e `Altura` foram perfeitamente extraídos, validados pelas réguas (6-14; 100-2000) e formatados com sucesso.
- 📁 **Reprovados:** Lista marcadores inconsistentes com a topologia (possuem apenas P, não têm ambos os números, faltam tags, ou os dados descritos não seguem padrão).

---

## 🛠 Bibliotecas e Setup

- **Python 3.9+** sugerido.
- Interface construída integralmente sob o padrão Qt usando a library port **PyQt6**.
- Parsing e parsing sub-hierárquico construído com The Element API nativa C-compatible (`xml.etree.ElementTree`).
- Testes desenvolvidos com framework **Pytest** integrado ao ecossistema Qt através das libraries **pytest-qt** e **pytest-mock**.

### Instalando as Bibliotecas
Caso seja rodar o código-fonte manualmente (ou trabalhar no CI/CD), instale os requirements:
```bash
pip install PyQt6 pytest pytest-cov pytest-qt pytest-mock requests-mock
```

---

## 🎮 Como Usar

Para inicializar a ferramenta, abra o prompt ou bash e execute o entrypoint primário da window:
```bash
python main_app.py
```

1. **Login de Acesso:** A tela principal tem uma injeção de `auth_logic` implementando credenciais pré-programadas para controle de acesso.
2. **KML Root Local:** Selecione o arquivo `.kml` a ser tradado na interface principal clicando em `Selecionar KML de Entrada...`.
3. **Mapeamento de Regras:** A barra da esquerda trará os modelos que agrupamos. Clique neles e escolha quais abas HTML (`<Data name="X">`) você deseja interceptar.
4. **Renomeie:** Configure (Opcionalmente) prefixos de texto ou sufixos manuais, configure com o que deseja separar o "DAN" da "Altura" (Ex: Traço `-` ou Barra `/`) e clique em **Renomear Marcadores**. Se sucesso, a janela exibirá as estatísticas de Aprovados/Reprovados para checagem em campo.

---

## 🧪 Suíte de Testes (QA 100% Coverage)

As funções possuem rotinas que abrangem até comportamentos extremos (como instanciar erro de hardware "Disco Cheio" corrompendo chamadas de write da library nativa OS do próprio Python).

Para rodar a verificação inteira localmente e auferir de fato `100%` da cobertura de todas as ramificações if/else:
```bash
pytest --cov=. --cov-report=term-missing
```

`Feito via orquestração e habilidades TDD da Suíte Avançada Antigravity Kit (Google Deepmind).`
