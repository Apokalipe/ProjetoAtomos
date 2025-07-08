# Projeto Átomos

**Átomos** é uma plataforma intuitiva e integrada que conecta, em um único ambiente visual, todas as etapas do processo de simulação molecular — da geração do sistema à análise avançada dos resultados.  
Desenvolvido em **Python com interface gráfica em PyQt6**, o Átomos tem como missão democratizar o uso de simulações computacionais para **cientistas experimentais**, eliminando barreiras técnicas e acelerando o avanço da pesquisa.

![image](https://github.com/user-attachments/assets/62ee8019-7b46-41a3-bcb7-56c1127909ce)

## Visão

Simulações moleculares são ferramentas poderosas, mas pouco acessíveis para quem não domina programação ou ferramentas específicas como LAMMPS, Packmol, OVITO ou scripts de análise.  
O Átomos surge para mudar isso, oferecendo uma **experiência visual, acessível e moderna**, sem abrir mão da profundidade científica.

![image](https://github.com/user-attachments/assets/af753204-4c66-4826-bc41-e383f0ecc4fc)

## Principais Módulos

### 1. Geração de Sistemas Moleculares
- Construção de estruturas 2D e 3D (ex: grafeno, lignina, óxidos)
- Inserção de grupos funcionais com controle de estequiometria
- Empacotamento de moléculas (Packmol-like)

### 2. Geração de Input e Execução de Simulações (LAMMPS)
- Criação automatizada de arquivos `.data` e `.lammps`
- Controle de parâmetros físicos e execuções locais com feedback
- Pré-configurações para simulações ReaxFF no LAMMPS

### 3. Análise de Resultados
- **Análise de Espécies Químicas:** identificação automática por conectividade
- **Análise Termodinâmica:** temperatura, energia, pressão, volume etc.
- **Análise Cinética:** quantificação de reações e evolução temporal
- **RDF e Difusão Atômica:** análise estrutural e dinâmica dos sistemas

![image](https://github.com/user-attachments/assets/af6fd366-8337-4dec-9e9c-2b6cf55ebabe)

## Diferenciais

- **Interface gráfica moderna** com PyQt6 (modo escuro incluso!)
- **Automação total** do fluxo de trabalho: do `.xyz` ao gráfico
- **Visualização interativa** e exportação de gráficos/publicações
- **Chega de scripts confusos e conversões manuais**  
  Você não precisa mais:
  - Passar horas montando o sistema no Packmol
  - Converter no OVITO
  - Escrever scripts Python para análise  
  > **CHEGA! O Átomos faz tudo por você.**

![image](https://github.com/user-attachments/assets/72b51334-28e2-4036-87e4-04f78652ad9b)

## Licença

Este projeto está sob **Todos os Direitos Reservados**.  
O uso, cópia, modificação ou distribuição do código **não são permitidos** sem autorização expressa do autor.

Para mais informações ou interesse em colaboração, entre em contato:
**felipepc@poli.ufrj.br**

---

## Desenvolvedor

**Felipe Pereira Costa**  
Nanotecnologista, UFRJ  
Pesquisador em simulações moleculares e inovação computacional aplicada à ciência de materiais.


