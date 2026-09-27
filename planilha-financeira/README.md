# Planilha Financeira Pessoal (Excel, sem macros)

Uma planilha para acompanhar receitas, despesas, cartões de crédito, contas fixas, orçamento, investimentos e metas. Todos os cálculos são fórmulas do Excel, então dá para ver e ajustar qualquer conta. Tudo está em português, com valores em R$ e datas no formato DD/MM/AAAA.

| Arquivo | Para que serve |
|---|---|
| `Planilha_Financeira_Pessoal.xlsx` | Versão **com dados fictícios** para você ver como tudo funciona. Os itens de exemplo terminam com "(exemplo)". |
| `Planilha_Financeira_Pessoal_em_branco.xlsx` | Versão **vazia**, para começar a usar de verdade. |
| `gerar_planilha.py` / `dados_exemplo.py` | Scripts que montam os dois arquivos (`python gerar_planilha.py`). |
| `validar_planilha.py` | Confere os resultados das fórmulas com um cálculo feito à parte, em Python. |

## Abas

**Início** (instruções e atalhos) · **Dashboard** · **Receitas** · **Despesas** · **Cartões de Crédito** · **Faturas** · **Contas Fixas** · **Orçamento Mensal** · **Investimentos** · **Metas Financeiras** · **Resumo Anual** · **Configurações** (onde ficam as listas de categorias e formas de pagamento)

## Como evitar lançar a mesma despesa duas vezes

- **Compra no cartão de crédito:** lance só na aba *Cartões de Crédito*, uma vez, com o número de parcelas. Cada parcela entra como despesa no mês em que a fatura vence. Compras feitas no dia do fechamento ou depois vão para a fatura seguinte.
- **Pagamento da fatura:** registre só na aba *Faturas*. Esse pagamento **não** conta como despesa, porque as compras já foram contadas. Ele serve para dar baixa na fatura e liberar o limite do cartão.
- Por isso, "Cartão de crédito" não aparece como forma de pagamento na aba *Despesas*.
- **Contas fixas:** cadastrar uma conta não cria despesa. Quando pagar, lance o valor em *Despesas* e escolha a conta em "Conta fixa vinculada". O status dela muda para "Paga".
- **Aportes em investimentos** vão só na aba *Investimentos*. Eles saem do saldo em conta, mas não contam como despesa.

## Uso ao longo dos anos

Todos os anos ficam nas mesmas listas. Para ver outro ano, basta trocar o filtro **Ano** no Dashboard: o Resumo Anual, as Contas Fixas, o Orçamento e os gráficos acompanham a mudança. As abas já vêm preparadas para 2.000 receitas, 6.000 despesas, 4.000 compras no cartão, 1.000 faturas e 3.000 movimentações de investimento.

As abas estão protegidas **sem senha**. Isso só impede que alguém apague uma fórmula sem querer. Para mudar a estrutura, use *Revisão > Desproteger Planilha*.

## Testes

```
RECALC=/caminho/para/recalc.py python validar_planilha.py
```

O script recalcula a planilha no LibreOffice e compara os resultados com um cálculo feito à parte. São dois cenários: **2026/setembro** e **2027/janeiro** com filtro de categoria. As verificações cobrem:

- totais de todos os meses (receitas, despesas, cartão, aportes, saldo, saldo acumulado, investimentos, dívida do cartão e patrimônio);
- a soma das categorias batendo com o total;
- as faturas de cada cartão por mês;
- o vencimento da 1ª parcela, inclusive compras feitas no dia do fechamento e na véspera;
- limite utilizado, status das faturas e status das contas fixas;
- pago × pendente e orçamento previsto × realizado;
- metas;
- parcelas que passam de um ano para o outro e a consolidação anual.

Resultado atual: **400 verificações, 0 falhas**. As duas planilhas completas também foram recalculadas sem nenhum erro de fórmula.
