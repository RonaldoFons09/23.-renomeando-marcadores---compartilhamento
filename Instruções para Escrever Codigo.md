# Instruções para Escrever Código Python de Excelência

Este guia expandido garante não apenas a legibilidade e a conformidade, mas também a confiabilidade, e a facilidade de manutenção do seu código, transformando-o em um padrão "production-ready".

---

## 1. Conformidade e Estilo Básico

PEP 8: Garanta total conformidade com o padrão oficial — incluindo indentação, espaçamento, nomes (snake_case, PascalCase), uso de docstrings e comprimento de linha (idealmente abaixo de 80 caracteres).

## 2. Legibilidade e Expressividade

Clareza (KISS): Priorize a clareza e a simplicidade. O código deve ser lido quase como prosa (Princípio KISS – Keep It Simple, Stupid).

Nomeação Semântica: Renomeie variáveis, funções e classes de forma descritiva e que expresse sua intenção ou ação.

- Funções/Métodos: Devem ser verbos de ação (ex: process_data, calculate_score).
- Booleanos: Devem ser prefixados por is_, has_, ou can_ (ex: is_valid, has_permission).

Pythonic Code: Use práticas idiomáticas de Python (ex: with para gerenciamento de recursos, enumerate para iteração com índice, zip, list/dict comprehensions).

## 3. Arquitetura e Manutenção

DRY (Don't Repeat Yourself): Elimine repetições criando funções ou classes reutilizáveis.

Princípio da Responsabilidade Única (SRP): Classes e funções devem ter apenas uma razão para mudar. Uma função deve fazer apenas uma coisa e fazê-la bem.

Modularidade e Separação de Preocupações: Isole a lógica de negócios central, a configuração, a interface e a persistência de dados (I/O, banco de dados) em módulos distintos.

## 4. Testabilidade e Confiabilidade

Testes Automatizados (CRUCIAL): Todo código funcional deve ter cobertura de testes unitários (ex: pytest). Os testes devem ser rápidos, independentes e repetíveis, cobrindo o comportamento esperado, casos de borda e tratamento de erros.

Tratamento de Erros: Garanta o uso apropriado de blocos try/except/finally. Capture apenas exceções específicas (nunca um except: vazio) e registre (log) os erros de forma útil.

## 5. Performance e Otimização

Identificação de Gargalos: Use ferramentas de profiling para apontar e otimizar loops e estruturas ineficientes, focando apenas onde o ganho é significativo.

Ferramentas Python Built-in: Prefira comprehensions, generators e funções built-in (ex: sum(), max(), map()) em vez de loops manuais sempre que possível.

## 6. Documentação e Tipagem

Docstrings Claras: Exija docstrings detalhadas em funções, métodos e classes (padrões Google ou reST são recomendados). Elas devem explicar o que o código faz, seus parâmetros, o que retorna e quais exceções podem ser levantadas.

Comentários: Use comentários para explicar o porquê de uma decisão (ex: "Por que essa otimização complexa foi necessária"), e não o que o código está fazendo (isso deve ser óbvio pela clareza do código).

Type Hints: Aplique anotações de tipo (Type Hints) em argumentos de função e valores de retorno para melhorar a legibilidade, a documentação e permitir a detecção estática de erros.

## 7. Ambiente e Dependências

Gerenciamento de Dependências: Use ferramentas como pip e um requirements.txt (ou ferramentas mais modernas como Poetry ou Conda) para definir e isolar estritamente as dependências do projeto, garantindo que o ambiente de execução seja reproduzível.

## 8. Logging

Níveis: DEBUG, INFO, WARNING, ERROR, CRITICAL

Nunca use print() em produção

Adicione contexto: user_id, request_id