"""Gera a Planilha Financeira Pessoal (.xlsx) — sem macros/VBA.

Uso:
    python gerar_planilha.py            # gera as duas versões (com exemplos e em branco)

Todas as contas são fórmulas do Excel; o Python só monta a estrutura,
a formatação e (opcionalmente) os lançamentos fictícios de exemplo.
"""
import calendar
import datetime as dt
import os
import sys

from openpyxl import Workbook
from openpyxl.chart import BarChart, LineChart, Reference, Series
from openpyxl.chart.label import DataLabelList
from openpyxl.comments import Comment
from openpyxl.formatting.rule import CellIsRule, DataBarRule, FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Protection, Side
from openpyxl.utils import get_column_letter as CL
from openpyxl.workbook.defined_name import DefinedName
from openpyxl.worksheet.datavalidation import DataValidation

import dados_exemplo as EX

# =============================================================== identidade visual
FONT = "Arial"
NAVY, TEAL, TEAL_L = "1F2A44", "0F766E", "E6F4F1"
CORAL, GOLD, SKY = "D1495B", "C9A227", "3A7CA5"
GRAY_BG, GRAY_TXT, BORDER_C = "F3F4F6", "6B7280", "D6DAE0"
INPUT_BG, INPUT_TXT = "FFF7E0", "1D4ED8"
RED_BG, RED_TXT, AMBER_BG, AMBER_TXT = "FDE2E2", "9B1C1C", "FEF3C7", "92400E"
GREEN_BG, GREEN_TXT = "DCFCE7", "166534"

BRL = '"R$" #,##0.00;[Red]-"R$" #,##0.00;"-"'
BRL0 = '"R$" #,##0.00;[Red]-"R$" #,##0.00;""'   # zero fica invisível
BRL_INT = '"R$" #,##0;[Red]-"R$" #,##0;"-"'
DATE = "dd/mm/yyyy"
MONTH = "mm/yyyy"
PCT = '0.0%;[Red]-0.0%;"-"'
INT = '0;-0;""'

thin = Side(style="thin", color=BORDER_C)
BOX = Border(left=thin, right=thin, top=thin, bottom=thin)
MESES = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho",
         "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
MES_AB = [m[:3] for m in MESES]


def fill(c):
    return PatternFill("solid", start_color=c, end_color=c)


def font(size=10, bold=False, color="1F2937", italic=False, underline=None):
    return Font(name=FONT, size=size, bold=bold, color=color, italic=italic, underline=underline)


def inp(c, fmt=None, align=None):
    """Célula de ENTRADA manual: fundo creme, texto azul, desbloqueada."""
    c.fill = fill(INPUT_BG)
    c.font = font(color=INPUT_TXT)
    c.border = BOX
    c.protection = Protection(locked=False)
    if fmt:
        c.number_format = fmt
    if align:
        c.alignment = Alignment(horizontal=align, vertical="center")


def calc(c, fmt=None, bold=False, align=None, color="1F2937", bg=GRAY_BG):
    """Célula de FÓRMULA: fundo cinza claro, texto escuro, bloqueada."""
    c.fill = fill(bg)
    c.font = font(bold=bold, color=color)
    c.border = BOX
    c.protection = Protection(locked=True)
    if fmt:
        c.number_format = fmt
    if align:
        c.alignment = Alignment(horizontal=align, vertical="center")


def header(ws, row, col, titles, height=30):
    for i, t in enumerate(titles):
        c = ws.cell(row=row, column=col + i, value=t)
        c.fill = fill(NAVY)
        c.font = font(bold=True, color="FFFFFF")
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        c.border = BOX
    ws.row_dimensions[row].height = height


def section(ws, cell, text, size=12):
    c = ws[cell]
    c.value = text
    c.font = font(size=size, bold=True, color=TEAL)


def note(ws, cell, text, color=GRAY_TXT, italic=True, size=9):
    c = ws[cell]
    c.value = text
    c.font = font(size=size, color=color, italic=italic)
    c.alignment = Alignment(vertical="center", wrap_text=False)


def top(ws, title, subtitle, widths, nav_col=None):
    ws.sheet_view.showGridLines = False
    ws.sheet_view.zoomScale = 90
    for col, w in widths.items():
        ws.column_dimensions[col].width = w
    ws["A1"].value = title
    ws["A1"].font = font(size=18, bold=True, color=NAVY)
    ws.row_dimensions[1].height = 32
    ws["A2"].value = subtitle
    ws["A2"].font = font(size=10, italic=True, color=GRAY_TXT)
    if nav_col:
        for i, (txt, dest) in enumerate([("⌂ Início", "Início"), ("▣ Dashboard", "Dashboard")]):
            c = ws.cell(row=1, column=nav_col + i, value=txt)
            c.hyperlink = f"#'{dest}'!A1"
            c.font = font(bold=True, color=SKY, underline="single")
            c.alignment = Alignment(horizontal="center", vertical="center")


def protect(ws):
    p = ws.protection
    p.sheet = True
    p.formatColumns = False
    p.formatRows = False
    p.formatCells = False
    p.autoFilter = False
    p.sort = False
    p.selectLockedCells = False
    p.selectUnlockedCells = False


def dv_list(ws, name, rng, msg):
    dv = DataValidation(type="list", formula1=f"={name}", allow_blank=True, showDropDown=False)
    dv.error = "Escolha um item da lista (edite as listas na aba Configurações)."
    dv.errorTitle = "Valor inválido"
    dv.prompt = msg
    dv.promptTitle = "Selecione"
    dv.showErrorMessage = True
    dv.showInputMessage = True
    ws.add_data_validation(dv)
    dv.add(rng)


def dv_date(ws, rng):
    dv = DataValidation(type="date", operator="between", formula1="36526", formula2="73415", allow_blank=True)
    dv.error = "Digite uma data válida no formato DD/MM/AAAA."
    dv.errorTitle = "Data inválida"
    dv.showErrorMessage = True
    ws.add_data_validation(dv)
    dv.add(rng)


def dv_num(ws, rng, mn="0", mx="1000000000", whole=False, msg="Digite um valor numérico positivo."):
    dv = DataValidation(type="whole" if whole else "decimal", operator="between", formula1=mn, formula2=mx, allow_blank=True)
    dv.error = msg
    dv.errorTitle = "Valor inválido"
    dv.showErrorMessage = True
    ws.add_data_validation(dv)
    dv.add(rng)


def add_name(wb, name, ref):
    wb.defined_names[name] = DefinedName(name, attr_text=ref)


# ============================================================= faixas de dados
_T = os.environ.get("PFP_TESTE") == "1"  # modo de teste: mesmas fórmulas, menos linhas (recálculo rápido)
R_REC = (6, 205 if _T else 2005)      # Receitas
R_DESP = (6, 405 if _T else 6005)     # Despesas
R_CC = (31, 230 if _T else 4030)      # Compras no cartão
R_FAT = (6, 105 if _T else 1005)      # Faturas
R_INV = (6, 205 if _T else 3005)      # Movimentações de investimentos
R_CF = (7, 106)        # Contas fixas
R_ATV = (6, 45)        # Ativos
R_META = (7, 36)       # Metas
N_CARTOES = 8
CAT_REC_ROWS = (13, 32)   # 20 categorias de receita (Configurações)
CAT_DESP_ROWS = (13, 52)  # 40 categorias de despesa

CAT_RECEITA = ["Salário", "13º salário", "Férias", "Renda extra / freelance",
               "Rendimentos de investimentos", "Aluguel recebido", "Reembolsos",
               "Presentes recebidos", "Outras receitas"]
CAT_DESPESA = ["Moradia", "Contas de consumo (água, luz, gás)", "Telefone e internet",
               "Supermercado", "Alimentação", "Transporte", "Saúde", "Educação",
               "Cuidados pessoais", "Lazer", "Vestuário", "Assinaturas e serviços",
               "Eletrônicos e eletrodomésticos", "Manutenção do lar", "Seguros",
               "Impostos e taxas", "Pets", "Filhos", "Viagens", "Presentes e doações",
               "Empréstimos e financiamentos", "Tarifas bancárias", "Outras despesas"]
FORMAS = ["Pix", "Cartão de débito", "Dinheiro", "Boleto", "Transferência (TED/DOC)",
          "Débito automático"]
TIPOS_INV = ["Reserva de emergência", "Renda fixa (CDB/LCI/LCA)", "Tesouro Direto", "Ações",
             "Fundos imobiliários (FII)", "Fundos de investimento", "Previdência privada",
             "Criptoativos", "Outros"]

SH = {  # nomes das abas
    "ini": "Início", "dash": "Dashboard", "rec": "Receitas", "desp": "Despesas",
    "cc": "Cartões de Crédito", "fat": "Faturas", "cf": "Contas Fixas",
    "orc": "Orçamento Mensal", "inv": "Investimentos", "meta": "Metas Financeiras",
    "res": "Resumo Anual", "cfg": "Configurações",
}


def q(key):
    return f"'{SH[key]}'"


# ============================================================ blocos de fórmula
def f_rec(d1, d2):
    return f'SUMIFS(Rec_Valor,Rec_Data,">="&{d1},Rec_Data,"<="&{d2})'


def f_desp(d1, d2):
    return f'SUMIFS(Desp_Valor,Desp_Data,">="&{d1},Desp_Data,"<="&{d2})'


def f_card(k):
    """Parcelas de cartão cuja fatura vence no mês de índice k (ano*12+mês)."""
    return f'SUMIFS(CC_Parcela,CC_Ini,"<="&{k},CC_Fim,">="&{k})'


def f_card_cum(k):
    """Total de parcelas faturadas até o mês k (inclusive)."""
    return (f"SUMPRODUCT(CC_Parcela*(CC_Ini>0)*(CC_Ini<={k})*"
            f"((CC_Fim<={k})*(CC_Fim-CC_Ini+1)+(CC_Fim>{k})*({k}-CC_Ini+1)))")


def f_card_future(k, d2):
    """Parcelas de compras já feitas até d2 que vencem depois do mês k (dívida futura)."""
    return (f"SUMPRODUCT(CC_Parcela*(CC_Data<={d2})*(CC_Fim>{k})*"
            f"((CC_Ini>{k})*(CC_Fim-CC_Ini+1)+(CC_Ini<={k})*(CC_Fim-{k})))")


def f_card_range(a, b):
    """Parcelas que vencem entre os meses de índice a e b (inclusive)."""
    mn = f"(CC_Fim-(CC_Fim>{b})*(CC_Fim-{b}))"
    mx = f"(CC_Ini+(CC_Ini<{a})*({a}-CC_Ini))"
    return f"SUMPRODUCT(CC_Parcela*(CC_Ini>0)*(({mn}-{mx}+1)>0)*({mn}-{mx}+1))"


def f_inv_net(d1, d2):
    return (f'(SUMIFS(Inv_Valor,Inv_Op,"Aporte",Inv_Data,">="&{d1},Inv_Data,"<="&{d2})'
            f'-SUMIFS(Inv_Valor,Inv_Op,"Resgate",Inv_Data,">="&{d1},Inv_Data,"<="&{d2}))')


def f_cash_cum(d2, k):
    """Saldo em conta ao fim do período: saldo inicial + receitas - despesas - cartão - aportes líquidos."""
    return (f'(cfg_SaldoInicial+SUMIFS(Rec_Valor,Rec_Data,"<="&{d2})-SUMIFS(Desp_Valor,Desp_Data,"<="&{d2})'
            f'-{f_card_cum(k)}'
            f'-(SUMIFS(Inv_Valor,Inv_Op,"Aporte",Inv_Data,"<="&{d2})-SUMIFS(Inv_Valor,Inv_Op,"Resgate",Inv_Data,"<="&{d2})))')


def f_inv_bal(d2):
    return f'SUMIFS(Inv_Efeito,Inv_Data,"<="&{d2})'


def f_pl(d2, k):
    return f"({f_cash_cum(d2, k)}+{f_inv_bal(d2)}-{f_card_future(k, d2)})"


# ============================================================ cálculo auxiliar
def primeira_fatura(data, fech, venc):
    """Vencimento da 1ª parcela: compras no dia do fechamento ou depois vão para a fatura seguinte."""
    m = data.month + (1 if data.day >= fech else 0) + (1 if venc <= fech else 0)
    y = data.year + (m - 1) // 12
    m = (m - 1) % 12 + 1
    return dt.date(y, m, min(venc, calendar.monthrange(y, m)[1]))


def fatura_valor(cartao, mes):
    card = {c[0]: c for c in EX.CARTOES}[cartao]
    k = mes.year * 12 + mes.month
    tot = 0.0
    for d, _, _, cc, val, n in EX.COMPRAS:
        if cc != cartao:
            continue
        f = primeira_fatura(d, card[3], card[4])
        ini = f.year * 12 + f.month
        if ini <= k <= ini + n - 1:
            tot += val / n
    return round(tot, 2)


# ================================================================== construção
def build(path, exemplos=True):
    wb = Workbook()
    ws0 = wb.active
    ws0.title = SH["ini"]
    sheets = {"ini": ws0}
    for key in ["dash", "rec", "desp", "cc", "fat", "cf", "orc", "inv", "meta", "res", "cfg"]:
        sheets[key] = wb.create_sheet(SH[key])
    tab_colors = {"ini": NAVY, "dash": TEAL, "rec": "2E8B57", "desp": CORAL, "cc": "7B4FA0",
                  "fat": "7B4FA0", "cf": "C0712F", "orc": GOLD, "inv": SKY, "meta": "2E8B57",
                  "res": NAVY, "cfg": "9CA3AF"}
    for k, ws in sheets.items():
        ws.sheet_properties.tabColor = tab_colors[k]

    # ---------------------------------------------------------------- nomes
    def rng(key, col, r):
        return f"{q(key)}!${col}${r[0]}:${col}${r[1]}"

    names = {
        "Rec_Data": rng("rec", "A", R_REC), "Rec_Cat": rng("rec", "C", R_REC),
        "Rec_Valor": rng("rec", "D", R_REC), "Rec_Status": rng("rec", "E", R_REC),
        "Desp_Data": rng("desp", "A", R_DESP), "Desp_Cat": rng("desp", "C", R_DESP),
        "Desp_Valor": rng("desp", "D", R_DESP), "Desp_Forma": rng("desp", "E", R_DESP),
        "Desp_Status": rng("desp", "F", R_DESP), "Desp_Conta": rng("desp", "G", R_DESP),
        "Desp_Alerta": rng("desp", "J", R_DESP),
        "CC_Data": rng("cc", "A", R_CC), "CC_Cat": rng("cc", "C", R_CC),
        "CC_Cartao": rng("cc", "D", R_CC), "CC_Valor": rng("cc", "E", R_CC),
        "CC_Parcela": rng("cc", "G", R_CC), "CC_Ini": rng("cc", "L", R_CC), "CC_Fim": rng("cc", "M", R_CC),
        "Fat_Cartao": rng("fat", "A", R_FAT), "Fat_Mes": rng("fat", "B", R_FAT),
        "Fat_Pago": rng("fat", "F", R_FAT), "Fat_Status": rng("fat", "H", R_FAT),
        "Inv_Data": rng("inv", "K", R_INV), "Inv_Ativo": rng("inv", "L", R_INV),
        "Inv_Op": rng("inv", "M", R_INV), "Inv_Valor": rng("inv", "N", R_INV),
        "Inv_Efeito": rng("inv", "P", R_INV),
        "cfg_SaldoInicial": f"{q('cfg')}!$D$4", "cfg_Alerta": f"{q('cfg')}!$D$5",
        "cfg_Hoje": f"{q('cfg')}!$D$6", "cfg_HojeIdx": f"{q('cfg')}!$D$7",
        "dash_Ano": f"{q('dash')}!$C$4", "dash_Mes": f"{q('dash')}!$F$4", "dash_Cat": f"{q('dash')}!$J$4",
        "dash_MesNum": f"{q('cfg')}!$D$8", "dash_D1": f"{q('cfg')}!$D$9", "dash_Idx": f"{q('cfg')}!$D$10",
        "Lista_Meses": f"{q('cfg')}!$M$13:$M$24", "Lista_Anos": f"{q('cfg')}!$N$13:$N$53",
        "Lista_StatusDesp": f"{q('cfg')}!$J$13:$J$14", "Lista_StatusRec": f"{q('cfg')}!$K$13:$K$14",
        "Lista_OpInv": f"{q('cfg')}!$L$13:$L$15",
    }

    def dyn(ref_first, ref_range):
        return f'OFFSET({ref_first},0,0,MAX(1,COUNTIF({ref_range},"?*")),1)'

    c = q("cfg")
    names["Lista_CatReceita"] = dyn(f"{c}!$B$13", f"{c}!$B$13:$B$32")
    names["Lista_CatDespesa"] = dyn(f"{c}!$D$13", f"{c}!$D$13:$D$52")
    names["Lista_Formas"] = dyn(f"{c}!$F$13", f"{c}!$F$13:$F$27")
    names["Lista_TiposInv"] = dyn(f"{c}!$H$13", f"{c}!$H$13:$H$27")
    names["Lista_FiltroCat"] = dyn(f"{c}!$O$13", f"{c}!$O$13:$O$53")
    names["Lista_Cartoes"] = dyn(f"{q('cc')}!$A$6", f"{q('cc')}!$A$6:$A$13")
    names["Lista_Contas"] = dyn(f"{q('cf')}!$A$7", f"{q('cf')}!$A$7:$A$106")
    names["Lista_Ativos"] = dyn(f"{q('inv')}!$A$6", f"{q('inv')}!$A$6:$A$45")
    for n, r in names.items():
        add_name(wb, n, r)

    build_config(sheets["cfg"], exemplos)
    build_receitas(sheets["rec"], exemplos)
    build_despesas(sheets["desp"], exemplos)
    build_cartoes(sheets["cc"], exemplos)
    build_faturas(sheets["fat"], exemplos)
    build_contas_fixas(sheets["cf"], exemplos)
    build_orcamento(sheets["orc"], exemplos)
    build_investimentos(sheets["inv"], exemplos)
    build_metas(sheets["meta"], exemplos)
    build_resumo(sheets["res"])
    build_dashboard(sheets["dash"], exemplos)
    build_inicio(sheets["ini"], exemplos)

    for k, ws in sheets.items():
        protect(ws)
    wb.active = 1
    wb.calculation.fullCalcOnLoad = True
    wb.save(path)


# ============================================================== Configurações
def build_config(ws, ex):
    top(ws, "Configurações e listas", "Edite aqui categorias, formas de pagamento e parâmetros. As listas suspensas das demais abas são atualizadas automaticamente.",
        {"A": 2, "B": 34, "C": 2, "D": 36, "E": 2, "F": 26, "G": 2, "H": 28, "I": 2, "J": 14, "K": 14, "L": 14, "M": 13, "N": 9, "O": 36}, nav_col=6)
    rows = [
        (4, "Saldo inicial em conta (R$)", EX.SALDO_INICIAL if ex else 0, BRL, True,
         "Soma dos saldos das contas correntes na data do primeiro lançamento da planilha."),
        (5, "Dias de antecedência para alertas", EX.DIAS_ALERTA, "0", True,
         "Contas e faturas que vencem dentro deste número de dias ficam destacadas."),
        (6, "Data de hoje", "=TODAY()", DATE, False, "Automático."),
        (7, "Índice do mês atual (ano×12+mês)", "=YEAR(D6)*12+MONTH(D6)", "0", False, "Uso interno."),
        (8, "Mês selecionado no Dashboard (nº)", "=IFERROR(MATCH(dash_Mes,Lista_Meses,0),MONTH(D6))", "0", False, "Uso interno."),
        (9, "1º dia do mês selecionado", "=DATE(dash_Ano,D8,1)", DATE, False, "Uso interno."),
        (10, "Índice do mês selecionado", "=dash_Ano*12+D8", "0", False, "Uso interno."),
    ]
    for r, label, val, fmt, is_input, tip in rows:
        ws.cell(row=r, column=2, value=label).font = font(bold=is_input)
        cell = ws.cell(row=r, column=4, value=val)
        (inp if is_input else calc)(cell, fmt)
        note(ws, f"F{r}", tip)

    lists = [
        ("B", "Categorias de receita", CAT_RECEITA, CAT_REC_ROWS, True),
        ("D", "Categorias de despesa", CAT_DESPESA, CAT_DESP_ROWS, True),
        ("F", "Formas de pagamento (exceto cartão de crédito)", FORMAS, (13, 27), True),
        ("H", "Tipos de investimento", TIPOS_INV, (13, 27), True),
        ("J", "Status despesa", ["Pago", "Pendente"], (13, 14), False),
        ("K", "Status receita", ["Recebido", "A receber"], (13, 14), False),
        ("L", "Operação invest.", ["Aporte", "Resgate", "Rendimento"], (13, 15), False),
        ("M", "Meses", MESES, (13, 24), False),
        ("N", "Anos", list(range(2020, 2061)), (13, 53), False),
    ]
    for col, title, items, (r0, r1), editable in lists:
        h = ws[f"{col}12"]
        h.value = title
        h.fill = fill(NAVY)
        h.font = font(bold=True, color="FFFFFF")
        h.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")
        for i, r in enumerate(range(r0, r1 + 1)):
            cell = ws[f"{col}{r}"]
            cell.value = items[i] if i < len(items) else None
            if editable:
                inp(cell)
            else:
                calc(cell)
    ws.row_dimensions[12].height = 42
    h = ws["O12"]
    h.value = "Filtro do Dashboard (automático)"
    h.fill = fill(NAVY)
    h.font = font(bold=True, color="FFFFFF")
    h.alignment = Alignment(wrap_text=True, horizontal="center", vertical="center")
    calc(ws["O13"])
    ws["O13"].value = "Todas"
    for i in range(40):
        cell = ws.cell(row=14 + i, column=15, value=f'=IF(D{13 + i}="","",D{13 + i})')
        calc(cell)
    note(ws, "B11", "Células creme = editáveis. Mantenha nomes únicos; renomear uma categoria não altera lançamentos antigos.")


# =================================================================== Receitas
def build_receitas(ws, ex):
    top(ws, "Receitas", "Salário, renda extra, rendimentos resgatados e outras entradas. Use 'A receber' para valores previstos.",
        {"A": 13, "B": 40, "C": 30, "D": 16, "E": 14, "F": 34, "G": 12}, nav_col=6)
    r0, r1 = R_REC
    ws["A3"].value = "Total lançado"
    ws["B3"].value = "=SUM(Rec_Valor)"
    ws["C3"].value = "Recebido / A receber"
    ws["D3"].value = '=SUMIFS(Rec_Valor,Rec_Status,"Recebido")'
    ws["E3"].value = '=SUMIFS(Rec_Valor,Rec_Status,"A receber")'
    for a in ["A3", "C3"]:
        ws[a].font = font(bold=True, color=GRAY_TXT)
    for a in ["B3", "D3", "E3"]:
        calc(ws[a], BRL, bold=True, color=TEAL, bg=TEAL_L)
    header(ws, 5, 1, ["Data", "Descrição", "Categoria", "Valor (R$)", "Status", "Observações", "Mês"])
    for r in range(r0, r1 + 1):
        inp(ws[f"A{r}"], DATE, "center")
        inp(ws[f"B{r}"])
        inp(ws[f"C{r}"])
        inp(ws[f"D{r}"], BRL0)
        inp(ws[f"E{r}"], align="center")
        inp(ws[f"F{r}"])
        cell = ws[f"G{r}"]
        cell.value = f'=IF(A{r}="","",DATE(YEAR(A{r}),MONTH(A{r}),1))'
        calc(cell, MONTH, align="center")
    if ex:
        for i, (d, desc, cat, val, st, obs) in enumerate(EX.RECEITAS):
            r = r0 + i
            ws[f"A{r}"], ws[f"B{r}"], ws[f"C{r}"] = d, desc, cat
            ws[f"D{r}"], ws[f"E{r}"], ws[f"F{r}"] = val, st, obs
    dv_date(ws, f"A{r0}:A{r1}")
    dv_list(ws, "Lista_CatReceita", f"C{r0}:C{r1}", "Categoria da receita")
    dv_num(ws, f"D{r0}:D{r1}")
    dv_list(ws, "Lista_StatusRec", f"E{r0}:E{r1}", "Recebido ou A receber")
    ws.conditional_formatting.add(f"A{r0}:G{r1}", FormulaRule(formula=[f'AND($A{r0}<>"",$E{r0}="A receber")'], font=Font(color=AMBER_TXT, name=FONT)))
    ws.freeze_panes = "B6"
    ws.auto_filter.ref = f"A5:G{r1}"


# =================================================================== Despesas
def build_despesas(ws, ex):
    top(ws, "Despesas", "Gastos pagos por Pix, débito, dinheiro, boleto etc. Compras no CARTÃO DE CRÉDITO vão na aba 'Cartões de Crédito' (não lance aqui a fatura).",
        {"A": 13, "B": 36, "C": 30, "D": 15, "E": 22, "F": 12, "G": 28, "H": 28, "I": 11, "J": 18}, nav_col=8)
    r0, r1 = R_DESP
    ws["A3"].value = "Total lançado"
    ws["B3"].value = "=SUM(Desp_Valor)"
    ws["C3"].value = "Pago / Pendente"
    ws["D3"].value = '=SUMIFS(Desp_Valor,Desp_Status,"Pago")'
    ws["E3"].value = '=SUMIFS(Desp_Valor,Desp_Status,"Pendente")'
    for a in ["A3", "C3"]:
        ws[a].font = font(bold=True, color=GRAY_TXT)
    for a in ["B3", "D3", "E3"]:
        calc(ws[a], BRL, bold=True, color=CORAL, bg="FBEAEC")
    header(ws, 5, 1, ["Data (pagamento ou vencimento)", "Descrição", "Categoria", "Valor (R$)",
                      "Forma de pagamento", "Status", "Conta fixa vinculada (opcional)", "Observações", "Mês", "Alerta"])
    for r in range(r0, r1 + 1):
        inp(ws[f"A{r}"], DATE, "center")
        for col in "BCEGH":
            inp(ws[f"{col}{r}"])
        inp(ws[f"D{r}"], BRL0)
        inp(ws[f"F{r}"], align="center")
        ws[f"I{r}"].value = f'=IF(A{r}="","",DATE(YEAR(A{r}),MONTH(A{r}),1))'
        calc(ws[f"I{r}"], MONTH, align="center")
        ws[f"J{r}"].value = (f'=IF(OR(A{r}="",F{r}<>"Pendente"),"",IF(A{r}<cfg_Hoje,"Vencida",'
                             f'IF(A{r}-cfg_Hoje<=cfg_Alerta,"Vence em "&(A{r}-cfg_Hoje)&" dia(s)","A vencer")))')
        calc(ws[f"J{r}"], align="center")
    if ex:
        for i, (d, desc, cat, val, forma, st, conta, obs) in enumerate(EX.DESPESAS):
            r = r0 + i
            for col, v in zip("ABCDEFGH", [d, desc, cat, val, forma, st, conta or None, obs or None]):
                ws[f"{col}{r}"] = v
    dv_date(ws, f"A{r0}:A{r1}")
    dv_list(ws, "Lista_CatDespesa", f"C{r0}:C{r1}", "Categoria da despesa")
    dv_num(ws, f"D{r0}:D{r1}")
    dv_list(ws, "Lista_Formas", f"E{r0}:E{r1}", "Cartão de crédito não aparece aqui de propósito: use a aba Cartões de Crédito.")
    dv_list(ws, "Lista_StatusDesp", f"F{r0}:F{r1}", "Pago ou Pendente")
    dv_list(ws, "Lista_Contas", f"G{r0}:G{r1}", "Se este lançamento paga uma conta fixa, selecione-a para a baixa automática.")
    cf = ws.conditional_formatting
    cf.add(f"A{r0}:J{r1}", FormulaRule(formula=[f'$J{r0}="Vencida"'], fill=fill(RED_BG), font=Font(color=RED_TXT, name=FONT)))
    cf.add(f"A{r0}:J{r1}", FormulaRule(formula=[f'LEFT($J{r0},8)="Vence em"'], fill=fill(AMBER_BG), font=Font(color=AMBER_TXT, name=FONT)))
    ws.freeze_panes = "B6"
    ws.auto_filter.ref = f"A5:J{r1}"


# ========================================================= Cartões de Crédito
def build_cartoes(ws, ex):
    top(ws, "Cartões de Crédito", "Cadastre os cartões e lance cada COMPRA uma única vez (com nº de parcelas). As faturas e os meses futuros são calculados automaticamente.",
        {"A": 30, "B": 34, "C": 26, "D": 20, "E": 14, "F": 10, "G": 14, "H": 13, "I": 13, "J": 12, "K": 14, "L": 9, "M": 9, "N": 13, "O": 9, "P": 9}, nav_col=10)
    section(ws, "A4", "1. Cadastro de cartões")
    header(ws, 5, 1, ["Cartão (nome único)", "Bandeira / banco", "Limite (R$)", "Dia de fechamento",
                      "Dia de vencimento", "", "Limite utilizado", "Limite disponível", "% utilizado",
                      "Fatura do mês atual", "Fatura do próximo mês", "", "", "Parcelas futuras (após mês atual)"])
    for i in range(N_CARTOES):
        r = 6 + i
        inp(ws[f"A{r}"])
        inp(ws[f"B{r}"])
        inp(ws[f"C{r}"], BRL0)
        inp(ws[f"D{r}"], INT, "center")
        inp(ws[f"E{r}"], INT, "center")
        forms = {
            "G": (f'=IF(A{r}="","",MAX(0,SUMIFS(CC_Valor,CC_Cartao,A{r})-SUMIFS(Fat_Pago,Fat_Cartao,A{r})))', BRL),
            "H": (f'=IF(OR(A{r}="",C{r}=""),"",C{r}-G{r})', BRL),
            "I": (f'=IF(OR(A{r}="",N(C{r})=0),"",G{r}/C{r})', PCT),
            "J": (f'=IF(A{r}="","",SUMIFS(CC_Parcela,CC_Cartao,A{r},CC_Ini,"<="&cfg_HojeIdx,CC_Fim,">="&cfg_HojeIdx))', BRL),
            "K": (f'=IF(A{r}="","",SUMIFS(CC_Parcela,CC_Cartao,A{r},CC_Ini,"<="&(cfg_HojeIdx+1),CC_Fim,">="&(cfg_HojeIdx+1)))', BRL),
            "N": (f'=IF(A{r}="","",SUMPRODUCT(CC_Parcela*(CC_Cartao=A{r})*(CC_Fim>cfg_HojeIdx)*((CC_Ini>cfg_HojeIdx)*(CC_Fim-CC_Ini+1)+(CC_Ini<=cfg_HojeIdx)*(CC_Fim-cfg_HojeIdx))))', BRL),
        }
        for col, (f, fmt) in forms.items():
            ws[f"{col}{r}"].value = f
            calc(ws[f"{col}{r}"], fmt)
    for col in "FLM":
        ws[f"{col}5"].fill = PatternFill(None)
        ws[f"{col}5"].border = Border()
    if ex:
        for i, (n, b, lim, fe, ve) in enumerate(EX.CARTOES):
            r = 6 + i
            ws[f"A{r}"], ws[f"B{r}"], ws[f"C{r}"], ws[f"D{r}"], ws[f"E{r}"] = n, b, lim, fe, ve
    dv_num(ws, "D6:E13", "1", "31", whole=True, msg="Informe um dia entre 1 e 31.")
    dv_num(ws, "C6:C13")
    ws.conditional_formatting.add("I6:I13", CellIsRule(operator="greaterThanOrEqual", formula=["0.8"], fill=fill(RED_BG), font=Font(color=RED_TXT, bold=True, name=FONT)))
    ws.conditional_formatting.add("I6:I13", DataBarRule(start_type="num", start_value=0, end_type="num", end_value=1, color="7B4FA0"))
    note(ws, "A14", "Limite utilizado = total das compras do cartão − total pago nas faturas (aba Faturas). Compra no dia do fechamento ou depois entra na fatura seguinte.")

    # ---------------------------------------------------- matriz de faturas
    section(ws, "A16", "2. Faturas por mês de vencimento — ano selecionado no Dashboard:")
    ws["D16"].value = "=dash_Ano"
    calc(ws["D16"], "0", bold=True, align="center", color=TEAL, bg=TEAL_L)
    header(ws, 17, 1, ["Cartão"] + MES_AB + ["Total do ano"])
    for i in range(N_CARTOES):
        r = 18 + i
        ws[f"A{r}"].value = f'=IF(A{6 + i}="","",A{6 + i})'
        calc(ws[f"A{r}"])
        for m in range(1, 13):
            col = CL(1 + m)
            ws[f"{col}{r}"].value = f'=IF($A{r}="",0,SUMIFS(CC_Parcela,CC_Cartao,$A{r},CC_Ini,"<="&(dash_Ano*12+{m}),CC_Fim,">="&(dash_Ano*12+{m})))'
            calc(ws[f"{col}{r}"], BRL0)
        ws[f"N{r}"].value = f"=SUM(B{r}:M{r})"
        calc(ws[f"N{r}"], BRL0, bold=True)
    labels = [(26, "Total das faturas", "=SUM({c}18:{c}25)"),
              (27, "Pago (aba Faturas)", '=SUMIFS(Fat_Pago,Fat_Mes,">="&DATE(dash_Ano,{m},1),Fat_Mes,"<="&EOMONTH(DATE(dash_Ano,{m},1),0))'),
              (28, "Em aberto", "=MAX(0,{c}26-{c}27)")]
    for r, lab, f in labels:
        ws[f"A{r}"].value = lab
        calc(ws[f"A{r}"], bold=True, bg=TEAL_L)
        for m in range(1, 14):
            col = CL(1 + m)
            if m == 13:
                ws[f"N{r}"].value = f"=SUM(B{r}:M{r})"
            else:
                ws[f"{col}{r}"].value = f.format(c=col, m=m)
            calc(ws[f"{col}{r}"], BRL, bold=True, bg=TEAL_L)
    ws.conditional_formatting.add("B28:M28", CellIsRule(operator="greaterThan", formula=["0.004"], font=Font(color=RED_TXT, bold=True, name=FONT)))

    # ------------------------------------------------------------- compras
    section(ws, "A29", "3. Compras no cartão (lance a compra uma vez; parcelas são distribuídas nas faturas)")
    r0, r1 = R_CC
    header(ws, 30, 1, ["Data da compra", "Descrição", "Categoria", "Cartão", "Valor total (R$)", "Nº parcelas",
                       "Valor da parcela", "Venc. 1ª parcela", "Venc. última parcela", "Parcelas já faturadas",
                       "Saldo a faturar", "Idx início", "Idx fim", "Fech.", "Venc."], height=36)
    for r in range(r0, r1 + 1):
        inp(ws[f"A{r}"], DATE, "center")
        inp(ws[f"B{r}"])
        inp(ws[f"C{r}"])
        inp(ws[f"D{r}"])
        inp(ws[f"E{r}"], BRL0)
        inp(ws[f"F{r}"], INT, "center")
        base = f"DATE(YEAR(A{r}),MONTH(A{r})+IF(DAY(A{r})>=N{r},1,0)+IF(O{r}<=N{r},1,0),1)"
        forms = {
            "N": (f'=IF(D{r}="","",IFERROR(INDEX($D$6:$D$13,MATCH(D{r},$A$6:$A$13,0)),""))', INT),
            "O": (f'=IF(D{r}="","",IFERROR(INDEX($E$6:$E$13,MATCH(D{r},$A$6:$A$13,0)),""))', INT),
            "H": (f'=IF(OR(A{r}="",N{r}="",O{r}=""),"",{base}+MIN(O{r},DAY(EOMONTH({base},0)))-1)', DATE),
            "I": (f'=IF(H{r}="","",EDATE(H{r},MAX(1,N(F{r}))-1))', DATE),
            "G": (f'=IF(OR(E{r}="",H{r}=""),0,E{r}/MAX(1,N(F{r})))', BRL0),
            "L": (f'=IF(H{r}="",0,YEAR(H{r})*12+MONTH(H{r}))', INT),
            "M": (f'=IF(H{r}="",0,L{r}+MAX(1,N(F{r}))-1)', INT),
            "J": (f'=IF(H{r}="","",MAX(0,MIN(M{r}-L{r}+1,cfg_HojeIdx-L{r}+1))&"/"&(M{r}-L{r}+1))', None),
            "K": (f'=IF(H{r}="",0,(M{r}-L{r}+1-MAX(0,MIN(M{r}-L{r}+1,cfg_HojeIdx-L{r}+1)))*G{r})', BRL0),
        }
        for col, (f, fmt) in forms.items():
            ws[f"{col}{r}"].value = f
            calc(ws[f"{col}{r}"], fmt, align="center" if col in "HIJLMNO" else None)
    if ex:
        for i, (d, desc, cat, card, val, n) in enumerate(EX.COMPRAS):
            r = r0 + i
            ws[f"A{r}"], ws[f"B{r}"], ws[f"C{r}"], ws[f"D{r}"], ws[f"E{r}"], ws[f"F{r}"] = d, desc, cat, card, val, n
    dv_date(ws, f"A{r0}:A{r1}")
    dv_list(ws, "Lista_CatDespesa", f"C{r0}:C{r1}", "Categoria do gasto")
    dv_list(ws, "Lista_Cartoes", f"D{r0}:D{r1}", "Cartão usado (cadastre no quadro 1)")
    dv_num(ws, f"E{r0}:E{r1}")
    dv_num(ws, f"F{r0}:F{r1}", "1", "72", whole=True, msg="Nº de parcelas entre 1 e 72.")
    ws.conditional_formatting.add(f"D{r0}:D{r1}", FormulaRule(formula=[f'AND($D{r0}<>"",$N{r0}="")'], fill=fill(RED_BG)))
    ws.column_dimensions.group("L", "O", hidden=True)
    ws.freeze_panes = "A31"
    ws.auto_filter.ref = f"A30:K{r1}"


# ==================================================================== Faturas
def build_faturas(ws, ex):
    top(ws, "Faturas", "Registre aqui o PAGAMENTO de cada fatura. O pagamento não é despesa: as compras já foram contadas por categoria — isso evita lançamento em duplicidade.",
        {"A": 30, "B": 14, "C": 14, "D": 17, "E": 15, "F": 17, "G": 15, "H": 20}, nav_col=6)
    r0, r1 = R_FAT
    ws["A3"].value = "Faturas registradas em aberto:"
    ws["A3"].font = font(bold=True, color=GRAY_TXT)
    ws["B3"].value = f'=SUMIFS(D{r0}:D{r1},F{r0}:F{r1},"",A{r0}:A{r1},"<>")'
    calc(ws["B3"], BRL, bold=True, color=CORAL, bg="FBEAEC")
    header(ws, 5, 1, ["Cartão", "Mês da fatura (vencimento)", "Vencimento", "Valor da fatura (calculado)",
                      "Data do pagamento", "Valor pago (R$)", "Diferença", "Status"], height=36)
    for r in range(r0, r1 + 1):
        inp(ws[f"A{r}"])
        inp(ws[f"B{r}"], MONTH, "center")
        inp(ws[f"E{r}"], DATE, "center")
        inp(ws[f"F{r}"], BRL0)
        forms = {
            "C": (f'=IF(OR(A{r}="",B{r}=""),"",IFERROR(DATE(YEAR(B{r}),MONTH(B{r}),MIN(INDEX({q("cc")}!$E$6:$E$13,MATCH(A{r},{q("cc")}!$A$6:$A$13,0)),DAY(EOMONTH(B{r},0)))),""))', DATE),
            "D": (f'=IF(OR(A{r}="",B{r}=""),"",SUMIFS(CC_Parcela,CC_Cartao,A{r},CC_Ini,"<="&(YEAR(B{r})*12+MONTH(B{r})),CC_Fim,">="&(YEAR(B{r})*12+MONTH(B{r}))))', BRL),
            "G": (f'=IF(OR(A{r}="",F{r}=""),"",F{r}-D{r})', BRL),
            "H": (f'=IF(OR(A{r}="",C{r}=""),"",IF(F{r}<>"",IF(F{r}>=D{r}-0.005,"Paga","Paga parcialmente"),'
                  f'IF(C{r}<cfg_Hoje,"Vencida",IF(C{r}-cfg_Hoje<=cfg_Alerta,"Vence em "&(C{r}-cfg_Hoje)&" dia(s)","A vencer"))))', None),
        }
        for col, (f, fmt) in forms.items():
            ws[f"{col}{r}"].value = f
            calc(ws[f"{col}{r}"], fmt, align="center" if col in "CH" else None)
    if ex:
        for i, (card, mes) in enumerate(EX.FATURAS_MESES):
            r = r0 + i
            ws[f"A{r}"], ws[f"B{r}"] = card, mes
            if (card, mes) not in EX.FATURAS_NAO_PAGAS:
                cc = {c[0]: c for c in EX.CARTOES}[card]
                ws[f"E{r}"] = dt.date(mes.year, mes.month, cc[4])
                ws[f"F{r}"] = fatura_valor(card, mes)
    dv_list(ws, "Lista_Cartoes", f"A{r0}:A{r1}", "Cartão")
    dv_date(ws, f"B{r0}:B{r1}")
    dv_date(ws, f"E{r0}:E{r1}")
    dv_num(ws, f"F{r0}:F{r1}")
    ws["B4"].value = "Digite 01/mm/aaaa"
    ws["B4"].font = font(size=8, italic=True, color=GRAY_TXT)
    cf = ws.conditional_formatting
    cf.add(f"A{r0}:H{r1}", FormulaRule(formula=[f'$H{r0}="Vencida"'], fill=fill(RED_BG), font=Font(color=RED_TXT, name=FONT)))
    cf.add(f"A{r0}:H{r1}", FormulaRule(formula=[f'LEFT($H{r0},8)="Vence em"'], fill=fill(AMBER_BG), font=Font(color=AMBER_TXT, name=FONT)))
    cf.add(f"H{r0}:H{r1}", FormulaRule(formula=[f'$H{r0}="Paga"'], font=Font(color=GREEN_TXT, bold=True, name=FONT)))
    cf.add(f"G{r0}:G{r1}", FormulaRule(formula=[f'AND(ISNUMBER($G{r0}),ABS($G{r0})>0.004)'], font=Font(color=RED_TXT, bold=True, name=FONT)))
    ws.freeze_panes = "B6"
    ws.auto_filter.ref = f"A5:H{r1}"


# =============================================================== Contas Fixas
def build_contas_fixas(ws, ex):
    widths = {"A": 30, "B": 28, "C": 14, "D": 9, "E": 18, "F": 12, "G": 12, "H": 9, "I": 12, "J": 14, "K": 18, "L": 12, "M": 13, "N": 2}
    for m in range(12):
        widths[CL(15 + m)] = 11
    top(ws, "Contas Fixas", "Despesas recorrentes. Para dar baixa, lance o pagamento em Despesas e selecione a conta em 'Conta fixa vinculada' — sem duplicar valores.",
        widths, nav_col=11)
    r0, r1 = R_CF
    ws["A3"].value = "Mês de referência (Dashboard):"
    ws["A3"].font = font(bold=True, color=GRAY_TXT)
    ws["B3"].value = "=dash_D1"
    calc(ws["B3"], MONTH, bold=True, color=TEAL, bg=TEAL_L, align="center")
    ws["C3"].value = "Previsto:"
    ws["D3"].value = f'=SUMIFS(C{r0}:C{r1},H{r0}:H{r1},"Sim")'
    ws["E3"].value = "Ainda não lançado:"
    ws["F3"].value = f"=SUM(M{r0}:M{r1})"
    for a in ["C3", "E3"]:
        ws[a].font = font(bold=True, color=GRAY_TXT)
        ws[a].alignment = Alignment(horizontal="right")
    ws.merge_cells("F3:G3")
    calc(ws["D3"], BRL, bold=True, color=TEAL, bg=TEAL_L)
    calc(ws["F3"], BRL, bold=True, color=CORAL, bg="FBEAEC")
    header(ws, 6, 1, ["Conta (nome único)", "Categoria", "Valor previsto", "Dia venc.", "Forma de pagamento",
                      "Início", "Fim (opcional)", "Ativa no mês?", "Vencimento no mês", "Lançado no mês",
                      "Status", "Diferença (lançado − previsto)", "A lançar (previsto)"], height=40)
    ws.merge_cells("O5:Z5")
    ws["O5"].value = "=\"Valores lançados em \"&dash_Ano&\" (verde = pago; vermelho = vencida sem lançamento)\""
    ws["O5"].font = font(bold=True, color=TEAL)
    header(ws, 6, 15, MES_AB, height=40)
    ref, eom = "dash_D1", "EOMONTH(dash_D1,0)"
    for r in range(r0, r1 + 1):
        inp(ws[f"A{r}"])
        inp(ws[f"B{r}"])
        inp(ws[f"C{r}"], BRL0)
        inp(ws[f"D{r}"], INT, "center")
        inp(ws[f"E{r}"])
        inp(ws[f"F{r}"], DATE, "center")
        inp(ws[f"G{r}"], DATE, "center")
        forms = {
            "H": (f'=IF(A{r}="","",IF(AND(OR(F{r}="",F{r}<={eom}),OR(G{r}="",G{r}>={ref})),"Sim","Não"))', None),
            "I": (f'=IF(OR(H{r}<>"Sim",D{r}=""),"",DATE(YEAR({ref}),MONTH({ref}),MIN(D{r},DAY({eom}))))', DATE),
            "J": (f'=IF(A{r}="",0,SUMIFS(Desp_Valor,Desp_Conta,A{r},Desp_Data,">="&{ref},Desp_Data,"<="&{eom}))', BRL0),
            "K": (f'=IF(A{r}="","",IF(H{r}<>"Sim","Inativa",IF(SUMIFS(Desp_Valor,Desp_Conta,A{r},Desp_Status,"Pago",Desp_Data,">="&{ref},Desp_Data,"<="&{eom})>0,"Paga",'
                  f'IF(I{r}="","Sem vencimento",IF(I{r}<cfg_Hoje,"Vencida",IF(I{r}-cfg_Hoje<=cfg_Alerta,"Vence em "&(I{r}-cfg_Hoje)&" dia(s)",IF(J{r}>0,"Lançada (pendente)","A vencer")))))))', None),
            "L": (f'=IF(OR(A{r}="",J{r}=0),"",J{r}-C{r})', BRL),
            "M": (f'=IF(AND(H{r}="Sim",J{r}=0),N(C{r}),0)', BRL0),
        }
        for col, (f, fmt) in forms.items():
            ws[f"{col}{r}"].value = f
            calc(ws[f"{col}{r}"], fmt, align="center" if col in "HIK" else None)
        for m in range(1, 13):
            col = CL(14 + m)
            d1 = f"DATE(dash_Ano,{m},1)"
            ws[f"{col}{r}"].value = f'=IF($A{r}="",0,SUMIFS(Desp_Valor,Desp_Conta,$A{r},Desp_Data,">="&{d1},Desp_Data,"<="&EOMONTH({d1},0)))'
            calc(ws[f"{col}{r}"], BRL0)
    if ex:
        for i, row in enumerate(EX.CONTAS_FIXAS):
            r = r0 + i
            for col, v in zip("ABCDEFG", row):
                ws[f"{col}{r}"] = v
    dv_list(ws, "Lista_CatDespesa", f"B{r0}:B{r1}", "Categoria")
    dv_num(ws, f"C{r0}:C{r1}")
    dv_num(ws, f"D{r0}:D{r1}", "1", "31", whole=True, msg="Dia entre 1 e 31.")
    dv_list(ws, "Lista_Formas", f"E{r0}:E{r1}", "Forma de pagamento")
    dv_date(ws, f"F{r0}:G{r1}")
    cf = ws.conditional_formatting
    cf.add(f"K{r0}:K{r1}", FormulaRule(formula=[f'$K{r0}="Vencida"'], fill=fill(RED_BG), font=Font(color=RED_TXT, bold=True, name=FONT)))
    cf.add(f"K{r0}:K{r1}", FormulaRule(formula=[f'LEFT($K{r0},8)="Vence em"'], fill=fill(AMBER_BG), font=Font(color=AMBER_TXT, bold=True, name=FONT)))
    cf.add(f"K{r0}:K{r1}", FormulaRule(formula=[f'$K{r0}="Paga"'], fill=fill(GREEN_BG), font=Font(color=GREEN_TXT, bold=True, name=FONT)))
    cf.add(f"A{r0}:M{r1}", FormulaRule(formula=[f'$H{r0}="Não"'], font=Font(color="9CA3AF", name=FONT)))
    grid = f"O{r0}:Z{r1}"
    d_venc = f"DATE(dash_Ano,COLUMN(O{r0})-14,MIN(MAX(1,N($D{r0})),DAY(EOMONTH(DATE(dash_Ano,COLUMN(O{r0})-14,1),0))))"
    cf.add(grid, FormulaRule(formula=[f"O{r0}>0"], fill=fill(GREEN_BG), font=Font(color=GREEN_TXT, name=FONT)))
    cf.add(grid, FormulaRule(formula=[f'AND($A{r0}<>"",O{r0}=0,{d_venc}<cfg_Hoje,OR($F{r0}="",$F{r0}<=EOMONTH(DATE(dash_Ano,COLUMN(O{r0})-14,1),0)),OR($G{r0}="",$G{r0}>=DATE(dash_Ano,COLUMN(O{r0})-14,1)))'],
                               fill=fill(RED_BG)))
    ws.freeze_panes = "B7"
    ws.auto_filter.ref = f"A6:M{r1}"


# =========================================================== Orçamento Mensal
def build_orcamento(ws, ex):
    widths = {"A": 32, "N": 15, "O": 2, "P": 14, "Q": 14, "R": 14, "S": 11, "T": 20, "U": 2, "V": 15, "W": 15, "X": 11}
    for m in range(12):
        widths[CL(2 + m)] = 11
    top(ws, "Orçamento Mensal", "Planeje quanto pretende gastar por categoria em cada mês (vale para todos os anos). O realizado vem de Despesas + Cartões automaticamente.",
        widths, nav_col=16)
    ws["A3"].value = "Comparativo do mês:"
    ws["A3"].font = font(bold=True, color=GRAY_TXT)
    ws["B3"].value = "=dash_D1"
    ws.merge_cells("B3:C3")
    calc(ws["B3"], MONTH, bold=True, color=TEAL, bg=TEAL_L, align="center")
    section(ws, "A5", "Planejado (R$) — preencha as células creme")
    section(ws, "P5", "Mês selecionado")
    section(ws, "V5", "Acumulado no ano")
    header(ws, 6, 1, ["Categoria (da aba Configurações)"] + MES_AB + ["Total anual"])
    header(ws, 6, 16, ["Previsto", "Realizado", "Saldo do orçamento", "% utilizado", "Situação"])
    header(ws, 6, 22, ["Previsto no ano", "Realizado no ano", "% utilizado"])
    ws["O6"].fill = PatternFill(None)
    ws["U6"].fill = PatternFill(None)
    for col in ("O", "U"):
        ws[f"{col}6"].border = Border()
    c0 = CAT_DESP_ROWS[0]
    for i in range(40):
        r = 7 + i
        rr = 33 + i  # linha correspondente no Resumo Anual
        ws[f"A{r}"].value = f"=IF({q('cfg')}!D{c0 + i}=\"\",\"\",{q('cfg')}!D{c0 + i})"
        calc(ws[f"A{r}"])
        for m in range(12):
            inp(ws.cell(row=r, column=2 + m), BRL0)
        ws[f"N{r}"].value = f"=SUM(B{r}:M{r})"
        calc(ws[f"N{r}"], BRL0, bold=True)
        forms = {
            "P": (f"=INDEX(B{r}:M{r},dash_MesNum)", BRL0),
            "Q": (f"=INDEX({q('res')}!B{rr}:M{rr},dash_MesNum)", BRL0),
            "R": (f'=IF(AND(P{r}=0,Q{r}=0),"",P{r}-Q{r})', BRL),
            "S": (f'=IF(P{r}>0,Q{r}/P{r},"")', PCT),
            "T": (f'=IF(A{r}="","",IF(AND(P{r}=0,Q{r}=0),"",IF(P{r}=0,"Sem orçamento",IF(Q{r}>P{r},"Acima do orçamento",IF(Q{r}>=0.9*P{r},"Atenção (≥ 90%)","Dentro do orçamento")))))', None),
            "V": (f"=N{r}", BRL0),
            "W": (f"={q('res')}!N{rr}", BRL0),
            "X": (f'=IF(V{r}>0,W{r}/V{r},"")', PCT),
        }
        for col, (f, fmt) in forms.items():
            ws[f"{col}{r}"].value = f
            calc(ws[f"{col}{r}"], fmt, align="center" if col == "T" else None)
    r = 47
    ws[f"A{r}"].value = "Sem categoria"
    calc(ws[f"A{r}"])
    ws[f"Q{r}"].value = f"=INDEX({q('res')}!B73:M73,dash_MesNum)"
    ws[f"W{r}"].value = f"={q('res')}!N73"
    for col in "QW":
        calc(ws[f"{col}{r}"], BRL0)
    r = 48
    ws[f"A{r}"].value = "TOTAL"
    calc(ws[f"A{r}"], bold=True, bg=TEAL_L)
    for col in [CL(c) for c in range(2, 15)] + ["P", "Q", "V", "W"]:
        ws[f"{col}{r}"].value = f"=SUM({col}7:{col}47)"
        calc(ws[f"{col}{r}"], BRL, bold=True, bg=TEAL_L)
    ws["R48"].value = "=P48-Q48"
    ws["S48"].value = '=IF(P48>0,Q48/P48,"")'
    ws["X48"].value = '=IF(V48>0,W48/V48,"")'
    calc(ws["R48"], BRL, bold=True, bg=TEAL_L)
    calc(ws["S48"], PCT, bold=True, bg=TEAL_L)
    calc(ws["X48"], PCT, bold=True, bg=TEAL_L)
    if ex:
        for i, cat in enumerate(CAT_DESPESA):
            if cat in EX.ORCAMENTO:
                for m in range(12):
                    ws.cell(row=7 + i, column=2 + m, value=EX.ORCAMENTO[cat])
    cf = ws.conditional_formatting
    cf.add("P7:T47", FormulaRule(formula=['$T7="Acima do orçamento"'], fill=fill(RED_BG), font=Font(color=RED_TXT, bold=True, name=FONT)))
    cf.add("P7:T47", FormulaRule(formula=['LEFT($T7,7)="Atenção"'], fill=fill(AMBER_BG), font=Font(color=AMBER_TXT, name=FONT)))
    cf.add("V7:X47", FormulaRule(formula=['AND($V7>0,$W7>$V7)'], fill=fill(RED_BG), font=Font(color=RED_TXT, bold=True, name=FONT)))
    cf.add("S7:S48", DataBarRule(start_type="num", start_value=0, end_type="num", end_value=1.5, color=GOLD))
    ws.freeze_panes = "B7"


# ============================================================== Investimentos
def build_investimentos(ws, ex):
    top(ws, "Investimentos", "Cadastre os ativos e registre aportes, resgates e rendimentos (valorização/desvalorização). Aportes saem do saldo em conta; não lance-os em Despesas.",
        {"A": 32, "B": 26, "C": 20, "D": 15, "E": 15, "F": 15, "G": 16, "H": 11, "I": 12, "J": 3,
         "K": 13, "L": 32, "M": 13, "N": 15, "O": 28, "P": 15, "Q": 10}, nav_col=12)
    ws["A3"].value = "Patrimônio investido (hoje):"
    ws["A3"].font = font(bold=True, color=GRAY_TXT)
    ws["B3"].value = f"=SUM(G{R_ATV[0]}:G{R_ATV[1]})"
    calc(ws["B3"], BRL, bold=True, color=SKY, bg="E3EEF6")
    section(ws, "A4", "1. Carteira (cadastro de ativos)")
    header(ws, 5, 1, ["Ativo / aplicação (nome único)", "Tipo", "Instituição", "Total aportado", "Total resgatado",
                      "Rendimentos acumulados", "Saldo atual", "% da carteira", "Rendimento s/ capital"], height=36)
    a0, a1 = R_ATV
    for r in range(a0, a1 + 1):
        inp(ws[f"A{r}"])
        inp(ws[f"B{r}"])
        inp(ws[f"C{r}"])
        forms = {
            "D": (f'=IF(A{r}="",0,SUMIFS(Inv_Valor,Inv_Ativo,A{r},Inv_Op,"Aporte"))', BRL0),
            "E": (f'=IF(A{r}="",0,SUMIFS(Inv_Valor,Inv_Ativo,A{r},Inv_Op,"Resgate"))', BRL0),
            "F": (f'=IF(A{r}="",0,SUMIFS(Inv_Valor,Inv_Ativo,A{r},Inv_Op,"Rendimento"))', BRL0),
            "G": (f"=D{r}-E{r}+F{r}", BRL0),
            "H": (f'=IF(OR(A{r}="",$B$3=0),"",G{r}/$B$3)', PCT),
            "I": (f'=IF(OR(A{r}="",D{r}-E{r}<=0),"",F{r}/(D{r}-E{r}))', PCT),
        }
        for col, (f, fmt) in forms.items():
            ws[f"{col}{r}"].value = f
            calc(ws[f"{col}{r}"], fmt)
    dv_list(ws, "Lista_TiposInv", f"B{a0}:B{a1}", "Tipo de investimento")
    ws.conditional_formatting.add(f"H{a0}:H{a1}", DataBarRule(start_type="num", start_value=0, end_type="num", end_value=1, color=SKY))

    section(ws, "A48", "2. Evolução mensal no ano selecionado no Dashboard")
    header(ws, 49, 1, ["Mês", "Aportes", "Resgates", "Rendimentos", "Saldo ao fim do mês", "Variação no mês"])
    for m in range(1, 13):
        r = 49 + m
        d1 = f"DATE(dash_Ano,{m},1)"
        d2 = f"EOMONTH({d1},0)"
        ws[f"A{r}"].value = MESES[m - 1]
        calc(ws[f"A{r}"])
        forms = {
            "B": f'=SUMIFS(Inv_Valor,Inv_Op,"Aporte",Inv_Data,">="&{d1},Inv_Data,"<="&{d2})',
            "C": f'=SUMIFS(Inv_Valor,Inv_Op,"Resgate",Inv_Data,">="&{d1},Inv_Data,"<="&{d2})',
            "D": f'=SUMIFS(Inv_Valor,Inv_Op,"Rendimento",Inv_Data,">="&{d1},Inv_Data,"<="&{d2})',
            "E": f"={f_inv_bal(d2)}",
            "F": f"=B{r}-C{r}+D{r}",
        }
        for col, f in forms.items():
            ws[f"{col}{r}"].value = f
            calc(ws[f"{col}{r}"], BRL)

    section(ws, "K4", "3. Movimentações")
    header(ws, 5, 11, ["Data", "Ativo", "Operação", "Valor (R$)", "Observação", "Efeito no saldo", "Mês"], height=36)
    r0, r1 = R_INV
    for r in range(r0, r1 + 1):
        inp(ws[f"K{r}"], DATE, "center")
        inp(ws[f"L{r}"])
        inp(ws[f"M{r}"], align="center")
        inp(ws[f"N{r}"], BRL0)
        inp(ws[f"O{r}"])
        ws[f"P{r}"].value = f'=IF(OR(K{r}="",N{r}=""),0,IF(M{r}="Resgate",-N{r},N{r}))'
        calc(ws[f"P{r}"], BRL0)
        ws[f"Q{r}"].value = f'=IF(K{r}="","",DATE(YEAR(K{r}),MONTH(K{r}),1))'
        calc(ws[f"Q{r}"], MONTH, align="center")
    if ex:
        for i, (n, t, inst) in enumerate(EX.ATIVOS):
            ws[f"A{a0 + i}"], ws[f"B{a0 + i}"], ws[f"C{a0 + i}"] = n, t, inst
        for i, (d, atv, op, val, obs) in enumerate(EX.MOVIMENTOS):
            r = r0 + i
            ws[f"K{r}"], ws[f"L{r}"], ws[f"M{r}"], ws[f"N{r}"] = d, atv, op, val
            ws[f"O{r}"] = obs or None
    dv_date(ws, f"K{r0}:K{r1}")
    dv_list(ws, "Lista_Ativos", f"L{r0}:L{r1}", "Ativo cadastrado no quadro 1")
    dv_list(ws, "Lista_OpInv", f"M{r0}:M{r1}", "Aporte, Resgate ou Rendimento (use valor negativo para desvalorização)")
    ws.freeze_panes = "A6"


# ======================================================================= Metas
def build_metas(ws, ex):
    top(ws, "Metas Financeiras", "Defina objetivos, valores e prazos. Vincule a meta a um investimento para acompanhar o progresso automaticamente.",
        {"A": 34, "B": 15, "C": 13, "D": 32, "E": 16, "F": 16, "G": 15, "H": 14, "I": 11, "J": 17, "K": 16}, nav_col=9)
    header(ws, 6, 1, ["Meta", "Valor alvo", "Prazo", "Investimento vinculado (opcional)",
                      "Valor acumulado (manual)", "Valor atual", "Quanto falta", "% realizado",
                      "Meses restantes", "Aporte mensal necessário", "Situação"], height=40)
    r0, r1 = R_META
    for r in range(r0, r1 + 1):
        inp(ws[f"A{r}"])
        inp(ws[f"B{r}"], BRL0)
        inp(ws[f"C{r}"], DATE, "center")
        inp(ws[f"D{r}"])
        inp(ws[f"E{r}"], BRL0)
        forms = {
            "F": (f'=IF(A{r}="","",IF(D{r}<>"",SUMIFS(Inv_Efeito,Inv_Ativo,D{r}),N(E{r})))', BRL),
            "G": (f'=IF(A{r}="","",MAX(0,N(B{r})-F{r}))', BRL),
            "H": (f'=IF(OR(A{r}="",N(B{r})=0),"",MIN(1,MAX(0,F{r}/B{r})))', PCT),
            "I": (f'=IF(OR(A{r}="",C{r}=""),"",MAX(0,(YEAR(C{r})-YEAR(cfg_Hoje))*12+MONTH(C{r})-MONTH(cfg_Hoje)))', INT),
            "J": (f'=IF(OR(A{r}="",G{r}=""),"",IF(G{r}=0,0,IF(N(I{r})>0,G{r}/I{r},G{r})))', BRL),
            "K": (f'=IF(A{r}="","",IF(G{r}=0,"Concluída",IF(AND(C{r}<>"",C{r}<cfg_Hoje),"Prazo vencido","Em andamento")))', None),
        }
        for col, (f, fmt) in forms.items():
            ws[f"{col}{r}"].value = f
            calc(ws[f"{col}{r}"], fmt, align="center" if col in "IK" else None)
    if ex:
        for i, (m, alvo, prazo, atv, man) in enumerate(EX.METAS):
            r = r0 + i
            ws[f"A{r}"], ws[f"B{r}"], ws[f"C{r}"] = m, alvo, prazo
            ws[f"D{r}"] = atv or None
            ws[f"E{r}"] = man
    dv_date(ws, f"C{r0}:C{r1}")
    dv_list(ws, "Lista_Ativos", f"D{r0}:D{r1}", "Opcional: o valor atual passa a ser o saldo deste investimento")
    dv_num(ws, f"B{r0}:B{r1}")
    cf = ws.conditional_formatting
    cf.add(f"H{r0}:H{r1}", DataBarRule(start_type="num", start_value=0, end_type="num", end_value=1, color="2E8B57"))
    cf.add(f"K{r0}:K{r1}", FormulaRule(formula=[f'$K{r0}="Concluída"'], fill=fill(GREEN_BG), font=Font(color=GREEN_TXT, bold=True, name=FONT)))
    cf.add(f"K{r0}:K{r1}", FormulaRule(formula=[f'$K{r0}="Prazo vencido"'], fill=fill(RED_BG), font=Font(color=RED_TXT, bold=True, name=FONT)))
    ws["A4"].value = "Total das metas:"
    ws["A4"].font = font(bold=True, color=GRAY_TXT)
    ws["B4"].value = f"=SUM(B{r0}:B{r1})"
    ws["E4"].value = "Acumulado:"
    ws["E4"].font = font(bold=True, color=GRAY_TXT)
    ws["E4"].alignment = Alignment(horizontal="right")
    ws["F4"].value = f"=SUM(F{r0}:F{r1})"
    ws["G4"].value = "Progresso geral:"
    ws["G4"].font = font(bold=True, color=GRAY_TXT)
    ws["H4"].value = '=IF(B4>0,F4/B4,"")'
    calc(ws["B4"], BRL, bold=True, color=TEAL, bg=TEAL_L)
    calc(ws["F4"], BRL, bold=True, color=TEAL, bg=TEAL_L)
    calc(ws["H4"], PCT, bold=True, color=TEAL, bg=TEAL_L)
    ws.freeze_panes = "B7"


# ================================================================ Resumo Anual
def build_resumo(ws):
    widths = {"A": 40, "N": 16, "O": 14, "P": 10}
    for m in range(12):
        widths[CL(2 + m)] = 13
    top(ws, "Resumo Anual", "Consolidação dos 12 meses do ano escolhido no Dashboard. Despesas de cartão entram no mês de vencimento da fatura (regime de caixa).",
        widths, nav_col=13)
    ws["A3"].value = "Ano (altere no Dashboard):"
    ws["A3"].font = font(bold=True, color=GRAY_TXT)
    ws["B3"].value = "=dash_Ano"
    calc(ws["B3"], "0", bold=True, color=TEAL, bg=TEAL_L, align="center")
    header(ws, 5, 1, ["Categoria / indicador"] + MES_AB + ["Total do ano", "Média mensal", "% do total"])
    for m in range(1, 13):
        col = CL(1 + m)
        ws[f"{col}6"].value = f"=DATE($B$3,{m},1)"
        ws[f"{col}7"].value = f"=YEAR({col}6)*12+MONTH({col}6)"
        calc(ws[f"{col}6"], DATE)
        calc(ws[f"{col}7"], "0")
    ws["A6"].value, ws["A7"].value = "1º dia do mês (auxiliar)", "Índice do mês (auxiliar)"
    ws.row_dimensions[6].hidden = True
    ws.row_dimensions[7].hidden = True

    def band(r, text, color):
        ws[f"A{r}"].value = text
        for cc in range(1, 17):
            cell = ws.cell(row=r, column=cc)
            cell.fill = fill(color)
            cell.font = font(bold=True, color="FFFFFF")

    def row_formula(r, label, fbuilder, fmt=BRL, bold=False, total="sum", bg=GRAY_BG, color="1F2937"):
        ws[f"A{r}"].value = label
        calc(ws[f"A{r}"], bold=bold, bg=bg, color=color)
        for m in range(1, 13):
            col = CL(1 + m)
            ws[f"{col}{r}"].value = "=" + fbuilder(col, m)
            calc(ws[f"{col}{r}"], fmt, bold=bold, bg=bg, color=color)
        if total == "sum":
            ws[f"N{r}"].value = f"=SUM(B{r}:M{r})"
            ws[f"O{r}"].value = f"=N{r}/12"
        elif total == "last":
            ws[f"N{r}"].value = f"=M{r}"
        elif total:
            ws[f"N{r}"].value = total
        for col in "NO":
            calc(ws[f"{col}{r}"], fmt, bold=True, bg=bg, color=color)
        calc(ws[f"P{r}"], PCT, bg=bg)

    d1 = lambda col: f"{col}$6"
    d2 = lambda col: f"EOMONTH({col}$6,0)"
    k = lambda col: f"{col}$7"

    band(8, "RECEITAS", "2E8B57")
    c0 = CAT_REC_ROWS[0]
    for i in range(20):
        r = 9 + i
        row_formula(r, None, lambda col, m, r=r: f'IF($A{r}="",0,SUMIFS(Rec_Valor,Rec_Cat,$A{r},Rec_Data,">="&{d1(col)},Rec_Data,"<="&{d2(col)}))', BRL0)
        ws[f"A{r}"].value = f"=IF({q('cfg')}!B{c0 + i}=\"\",\"\",{q('cfg')}!B{c0 + i})"
        ws[f"P{r}"].value = f'=IF($N$30=0,"",N{r}/$N$30)'
    row_formula(29, "Sem categoria", lambda col, m: f"{col}30-SUM({col}9:{col}28)", BRL0)
    ws["P29"].value = '=IF($N$30=0,"",N29/$N$30)'
    row_formula(30, "TOTAL DE RECEITAS", lambda col, m: f_rec(d1(col), d2(col)), bold=True, bg="DCFCE7", color=GREEN_TXT)

    band(32, "DESPESAS (contas + cartão por mês de vencimento da fatura)", CORAL)
    c0 = CAT_DESP_ROWS[0]
    for i in range(40):
        r = 33 + i
        row_formula(r, None, lambda col, m, r=r: (f'IF($A{r}="",0,SUMIFS(Desp_Valor,Desp_Cat,$A{r},Desp_Data,">="&{d1(col)},Desp_Data,"<="&{d2(col)})'
                                                  f'+SUMIFS(CC_Parcela,CC_Cat,$A{r},CC_Ini,"<="&{k(col)},CC_Fim,">="&{k(col)}))'), BRL0)
        ws[f"A{r}"].value = f"=IF({q('cfg')}!D{c0 + i}=\"\",\"\",{q('cfg')}!D{c0 + i})"
        ws[f"P{r}"].value = f'=IF($N$74=0,"",N{r}/$N$74)'
    row_formula(73, "Sem categoria", lambda col, m: f"{col}74-SUM({col}33:{col}72)", BRL0)
    ws["P73"].value = '=IF($N$74=0,"",N73/$N$74)'
    row_formula(74, "TOTAL DE DESPESAS", lambda col, m: f"{col}75+{col}76", bold=True, bg="FBEAEC", color=RED_TXT)
    row_formula(75, "   via cartão de crédito (faturas)", lambda col, m: f_card(k(col)))
    row_formula(76, "   via conta (Pix, débito, boleto...)", lambda col, m: f_desp(d1(col), d2(col)))

    band(78, "RESULTADO", NAVY)
    row_formula(79, "Aportes líquidos em investimentos", lambda col, m: f_inv_net(d1(col), d2(col)))
    row_formula(80, "SALDO DO MÊS (receitas − despesas − aportes)", lambda col, m: f"{col}30-{col}74-{col}79", bold=True, bg=TEAL_L, color=TEAL)
    row_formula(81, "Saldo acumulado em conta", lambda col, m: f_cash_cum(d2(col), k(col)), bold=True, total="last")
    row_formula(82, "Comprometimento da renda", lambda col, m: f'IF({col}30>0,{col}74/{col}30,"")', PCT,
                total='=IF(N30>0,N74/N30,"")')
    ws["O82"].value = None
    row_formula(83, "Orçamento previsto (aba Orçamento Mensal)", lambda col, m: f"SUM({q('orc')}!{col}7:{col}46)")
    row_formula(84, "Saldo do orçamento (previsto − realizado)", lambda col, m: f"{col}83-({col}74-{col}73)")

    band(86, "PATRIMÔNIO", SKY)
    row_formula(87, "Saldo investido", lambda col, m: f_inv_bal(d2(col)), total="last")
    row_formula(88, "Dívida de cartão (parcelas futuras)", lambda col, m: f_card_future(k(col), d2(col)), total="last")
    row_formula(89, "PATRIMÔNIO LÍQUIDO (conta + investimentos − dívidas)", lambda col, m: f"{col}81+{col}87-{col}88", bold=True, total="last", bg="E3EEF6", color=SKY)
    row_formula(90, "Variação patrimonial no mês",
                lambda col, m: (f"B89-{f_pl('(B$6-1)', '(B$7-1)')}" if m == 1 else f"{col}89-{CL(m)}89"))
    for r in (81, 87, 88, 89):
        ws[f"O{r}"].value = None
    note(ws, "A91", "Saldo acumulado = saldo inicial (Configurações) + receitas − despesas − faturas − aportes líquidos, desde o primeiro lançamento. Inclui valores pendentes/a receber já lançados.")

    # CF: categoria acima do orçamento no mês
    ws.conditional_formatting.add("B33:M72", FormulaRule(
        formula=[f"AND({q('orc')}!B7>0,B33>{q('orc')}!B7)"], fill=fill(RED_BG), font=Font(color=RED_TXT, bold=True, name=FONT)))
    ws.conditional_formatting.add("B80:N81", CellIsRule(operator="lessThan", formula=["0"], fill=fill(RED_BG), font=Font(color=RED_TXT, bold=True, name=FONT)))
    ws.conditional_formatting.add("B82:N82", CellIsRule(operator="greaterThan", formula=["1"], fill=fill(RED_BG), font=Font(color=RED_TXT, bold=True, name=FONT)))
    ws.conditional_formatting.add("B84:N84", CellIsRule(operator="lessThan", formula=["0"], font=Font(color=RED_TXT, bold=True, name=FONT)))

    # ----------------------------------------------- comparativo entre anos
    band(93, "COMPARATIVO ENTRE ANOS (5 anos anteriores + ano selecionado)", NAVY)
    header(ws, 94, 1, ["Ano", "Receitas", "Despesas", "Aportes líquidos", "Saldo do ano", "Patrimônio no fim do ano", "Variação do patrimônio", "Comprometimento", "", "Idx jan", "Idx dez"], height=36)
    for i in range(6):
        r = 95 + i
        a = f"DATE(A{r},1,1)"
        b = f"DATE(A{r},12,31)"
        forms = {
            "A": (f"=$B$3-{5 - i}", "0"),
            "J": (f"=A{r}*12+1", "0"),
            "K": (f"=A{r}*12+12", "0"),
            "B": ("=" + f_rec(a, b), BRL),
            "C": (f"={f_desp(a, b)}+{f_card_range(f'J{r}', f'K{r}')}", BRL),
            "D": ("=" + f_inv_net(a, b), BRL),
            "E": (f"=B{r}-C{r}-D{r}", BRL),
            "F": ("=" + f_pl(b, f"K{r}"), BRL),
            "G": (f"=F{r}-{f_pl(f'DATE(A{r}-1,12,31)', f'(J{r}-1)')}", BRL),
            "H": (f'=IF(B{r}>0,C{r}/B{r},"")', PCT),
        }
        for col, (f, fmt) in forms.items():
            ws[f"{col}{r}"].value = f
            calc(ws[f"{col}{r}"], fmt, bold=(i == 5), align="center" if col == "A" else None, bg=TEAL_L if i == 5 else GRAY_BG)
    ws.column_dimensions.group("J", "K", hidden=False)
    ws.conditional_formatting.add("E95:G100", CellIsRule(operator="lessThan", formula=["0"], font=Font(color=RED_TXT, bold=True, name=FONT)))
    ws.freeze_panes = "B6"


# =================================================================== Dashboard
def build_dashboard(ws, ex):
    widths = {"A": 2}
    for i in range(2, 18):
        widths[CL(i)] = 14
    top(ws, "Central Financeira Pessoal", "Visão geral: quanto entra, quanto sai, compromissos previstos e evolução do patrimônio.", widths, nav_col=None)
    ws["A1"].value = None
    ws["B1"].value = "Central Financeira Pessoal"
    ws["B1"].font = font(size=22, bold=True, color=NAVY)
    ws["A2"].value = None
    ws["B2"].value = "Visão geral: quanto entra, quanto sai, compromissos previstos e evolução do patrimônio."
    ws["B2"].font = font(size=10, italic=True, color=GRAY_TXT)
    ws["L1"].value = "Hoje:"
    ws["L1"].alignment = Alignment(horizontal="right", vertical="center")
    ws["L1"].font = font(color=GRAY_TXT)
    ws["M1"].value = "=cfg_Hoje"
    ws["M1"].number_format = DATE
    ws["M1"].font = font(bold=True, color=NAVY)
    ws["M1"].alignment = Alignment(vertical="center")
    # filtros
    ws.row_dimensions[4].height = 26
    for lab_cell, val_cell, merge, label, value, lst, msg in [
        ("B4", "C4", None, "ANO", EX.HOJE_REF.year, "Lista_Anos", "Ano a analisar"),
        ("E4", "F4", "F4:G4", "MÊS", MESES[EX.HOJE_REF.month - 1], "Lista_Meses", "Mês dos indicadores"),
        ("I4", "J4", "J4:L4", "CATEGORIA", "Todas", "Lista_FiltroCat", "Filtra o indicador e o gráfico de categoria"),
    ]:
        ws[lab_cell].value = label
        ws[lab_cell].font = font(bold=True, color="FFFFFF")
        ws[lab_cell].fill = fill(NAVY)
        ws[lab_cell].alignment = Alignment(horizontal="center", vertical="center")
        if merge:
            ws.merge_cells(merge)
        ws[val_cell].value = value
        inp(ws[val_cell], "0" if label == "ANO" else None, "center")
        ws[val_cell].font = font(size=12, bold=True, color=INPUT_TXT)
        dv_list(ws, lst, val_cell, msg)
    note(ws, "N4", "◄ filtros: altere ano, mês e categoria", color=TEAL, italic=True)

    B = 76  # primeira linha da tabela mensal-base
    mes_row = f"(dash_MesNum+{B - 1})"

    def mref(col):
        return f"INDEX(${col}${B}:${col}${B + 11},dash_MesNum)"

    pago = ('SUMIFS(Desp_Valor,Desp_Status,"Pago",Desp_Data,">="&dash_D1,Desp_Data,"<="&EOMONTH(dash_D1,0))'
            '+SUMIFS(Fat_Pago,Fat_Mes,">="&dash_D1,Fat_Mes,"<="&EOMONTH(dash_D1,0))')
    pend = ('SUMIFS(Desp_Valor,Desp_Status,"Pendente",Desp_Data,">="&dash_D1,Desp_Data,"<="&EOMONTH(dash_D1,0))'
            f'+MAX(0,{f_card("dash_Idx")}-SUMIFS(Fat_Pago,Fat_Mes,">="&dash_D1,Fat_Mes,"<="&EOMONTH(dash_D1,0)))'
            f"+{q('cf')}!$F$3")
    arec = 'SUMIFS(Rec_Valor,Rec_Status,"A receber",Rec_Data,">="&dash_D1,Rec_Data,"<="&EOMONTH(dash_D1,0))'
    catm = f'IF(dash_Cat="Todas",{mref("I")},IFERROR(INDEX({q("res")}!$B$33:$M$72,MATCH(dash_Cat,{q("res")}!$A$33:$A$72,0),dash_MesNum),0))'
    cata = f'IF(dash_Cat="Todas",SUM($I${B}:$I${B + 11}),IFERROR(INDEX({q("res")}!$N$33:$N$72,MATCH(dash_Cat,{q("res")}!$A$33:$A$72,0)),0))'
    orc_cat = f'IF(dash_Cat="Todas",INDEX({q("orc")}!$B$48:$M$48,dash_MesNum),IFERROR(INDEX({q("orc")}!$B$7:$M$46,MATCH(dash_Cat,{q("orc")}!$A$7:$A$46,0),dash_MesNum),0))'
    venc = (f'COUNTIF({q("cf")}!$K$7:$K$106,"Vencida")+COUNTIF(Desp_Alerta,"Vencida")+COUNTIF(Fat_Status,"Vencida")')
    avenc = (f'COUNTIF({q("cf")}!$K$7:$K$106,"Vence em*")+COUNTIF(Desp_Alerta,"Vence em*")+COUNTIF(Fat_Status,"Vence em*")')

    cards = [
        # (linha, col, título, fórmula, formato, cor, sub-rótulo, sub-fórmula, sub-formato)
        (6, 2, "RECEITAS DO MÊS", mref("F"), BRL, "2E8B57", "A receber", arec, BRL),
        (6, 4, "DESPESAS DO MÊS", mref("I"), BRL, CORAL, "Via cartão", mref("H"), BRL),
        (6, 6, "SALDO DO MÊS", mref("K"), BRL, TEAL, "Aportes líquidos", mref("J"), BRL),
        (6, 8, "SALDO ACUMULADO EM CONTA", mref("L"), BRL, NAVY, "Saldo inicial", "cfg_SaldoInicial", BRL),
        (6, 10, "COMPROMETIMENTO DA RENDA", mref("Q"), PCT, GOLD, "Meta sugerida", "0.7", PCT),
        (6, 12, "PATRIMÔNIO LÍQUIDO", mref("O"), BRL, SKY, "Variação no mês", f"INDEX({q('res')}!$B$90:$M$90,dash_MesNum)", BRL),
        (10, 2, "PAGO NO MÊS", pago, BRL, "2E8B57", "Inclui faturas pagas", None, None),
        (10, 4, "PENDENTE NO MÊS", pend, BRL, CORAL, "Contas fixas não lançadas", f"{q('cf')}!$F$3", BRL),
        (10, 6, "FATURAS DE CARTÃO (MÊS)", mref("H"), BRL, "7B4FA0", "Em aberto", f"MAX(0,{mref('H')}-SUMIFS(Fat_Pago,Fat_Mes,\">=\"&dash_D1,Fat_Mes,\"<=\"&EOMONTH(dash_D1,0)))", BRL),
        (10, 8, "SALDO INVESTIDO", mref("M"), BRL, SKY, "Aporte líquido no mês", mref("J"), BRL),
        (10, 10, "DÍVIDA DE CARTÃO (FUTURA)", mref("N"), BRL, CORAL, "Parcelas após o mês", None, None),
        (10, 12, "ALERTAS: VENCIDAS", venc, "0", RED_TXT, "Vencem em breve", avenc, "0"),
        (14, 2, "RECEITAS NO ANO", f"SUM($F${B}:$F${B + 11})", BRL, "2E8B57", "Média mensal", f"SUM($F${B}:$F${B + 11})/12", BRL),
        (14, 4, "DESPESAS NO ANO", f"SUM($I${B}:$I${B + 11})", BRL, CORAL, "Média mensal", f"SUM($I${B}:$I${B + 11})/12", BRL),
        (14, 6, "SALDO DO ANO", f"SUM($K${B}:$K${B + 11})", BRL, TEAL, "Comprometimento", f'IF(SUM($F${B}:$F${B + 11})>0,SUM($I${B}:$I${B + 11})/SUM($F${B}:$F${B + 11}),"")', PCT),
        (14, 8, "CATEGORIA: GASTO NO MÊS", catm, BRL, GOLD, "Orçado no mês", orc_cat, BRL),
        (14, 10, "CATEGORIA: GASTO NO ANO", cata, BRL, GOLD, "Média mensal", f"({cata})/12", BRL),
        (14, 12, "METAS: PROGRESSO GERAL", f"{q('meta')}!$H$4", PCT, "2E8B57", "Falta acumular", f"SUM({q('meta')}!$G$7:$G$36)", BRL),
    ]
    for r, c, title, f, fmt, color, sub, subf, subfmt in cards:
        c1, c2 = CL(c), CL(c + 1)
        for rr in range(r, r + 3):
            for cc in (c, c + 1):
                cell = ws.cell(row=rr, column=cc)
                cell.fill = fill("FFFFFF" if rr > r else color)
                cell.border = Border(left=Side(style="thin", color=BORDER_C) if cc == c else None,
                                     right=Side(style="thin", color=BORDER_C) if cc == c + 1 else None,
                                     top=Side(style="thin", color=BORDER_C) if rr == r else None,
                                     bottom=Side(style="medium", color=color) if rr == r + 2 else None)
                cell.protection = Protection(locked=True)
        ws.merge_cells(f"{c1}{r}:{c2}{r}")
        ws[f"{c1}{r}"].value = title
        ws[f"{c1}{r}"].font = font(size=8, bold=True, color="FFFFFF")
        ws[f"{c1}{r}"].alignment = Alignment(horizontal="center", vertical="center")
        ws.merge_cells(f"{c1}{r + 1}:{c2}{r + 1}")
        ws[f"{c1}{r + 1}"].value = "=" + f
        ws[f"{c1}{r + 1}"].number_format = fmt
        ws[f"{c1}{r + 1}"].font = font(size=15, bold=True, color=color if color != GOLD else "8A6D0B")
        ws[f"{c1}{r + 1}"].alignment = Alignment(horizontal="center", vertical="center")
        ws[f"{c1}{r + 2}"].value = sub
        ws[f"{c1}{r + 2}"].font = font(size=8, color=GRAY_TXT)
        if subf:
            ws[f"{c2}{r + 2}"].value = "=" + subf
            ws[f"{c2}{r + 2}"].number_format = subfmt
            ws[f"{c2}{r + 2}"].font = font(size=8, bold=True, color=GRAY_TXT)
            ws[f"{c2}{r + 2}"].alignment = Alignment(horizontal="right")
        ws.row_dimensions[r].height = 18
        ws.row_dimensions[r + 1].height = 30
        ws.row_dimensions[r + 2].height = 15
    ws.conditional_formatting.add("B7:M7", CellIsRule(operator="lessThan", formula=["0"], font=Font(color="C0392B", bold=True, size=15, name=FONT)))
    ws.conditional_formatting.add("J7", CellIsRule(operator="greaterThan", formula=["0.9"], fill=fill(RED_BG)))
    ws.conditional_formatting.add("L11", CellIsRule(operator="greaterThan", formula=["0"], fill=fill(RED_BG)))
    ws.conditional_formatting.add("H15", FormulaRule(formula=["AND(I16>0,H15>I16)"], fill=fill(RED_BG)))
    ws["F14"].value = '="SALDO DO ANO "&dash_Ano'
    ws["H14"].value = '="GASTO NO MÊS: "&UPPER(dash_Cat)'
    ws["J14"].value = '="GASTO NO ANO: "&UPPER(dash_Cat)'

    # ------------------------------------------------ base de cálculo
    section(ws, f"B{B - 3}", "Base de cálculo do Dashboard (automática — não editar)", size=11)
    header(ws, B - 1, 2, ["Mês", "Nº", "1º dia", "Índice", "Receitas", "Despesas em conta", "Faturas de cartão",
                          "Despesas totais", "Aportes líquidos", "Saldo do mês", "Saldo acumulado", "Saldo investido",
                          "Dívida cartão futura", "Patrimônio líquido", "Categoria filtrada", "Comprometimento"], height=36)
    res_map = {"F": 30, "G": 76, "H": 75, "I": 74, "J": 79, "K": 80, "L": 81, "M": 87, "N": 88, "O": 89, "Q": 82}
    for m in range(1, 13):
        r = B - 1 + m
        rc = CL(1 + m)  # coluna no Resumo Anual
        ws[f"B{r}"].value = MES_AB[m - 1]
        ws[f"C{r}"].value = m
        ws[f"D{r}"].value = f"=DATE(dash_Ano,C{r},1)"
        ws[f"E{r}"].value = f"=YEAR(D{r})*12+MONTH(D{r})"
        for col, rr in res_map.items():
            ws[f"{col}{r}"].value = f"={q('res')}!{rc}{rr}"
        ws[f"P{r}"].value = f'=IF(dash_Cat="Todas",I{r},IFERROR(INDEX({q("res")}!{rc}$33:{rc}$72,MATCH(dash_Cat,{q("res")}!$A$33:$A$72,0)),0))'
        for col in "BCDEFGHIJKLMNOPQ":
            fmt = {"B": None, "C": "0", "D": DATE, "E": "0", "Q": PCT}.get(col, BRL)
            calc(ws[f"{col}{r}"], fmt)
    ws.conditional_formatting.add(f"F{B}:Q{B + 11}", FormulaRule(formula=[f"$C{B}=dash_MesNum"], fill=fill(TEAL_L), font=Font(bold=True, name=FONT)))

    # categorias do mês/ano + top 10
    C0 = B + 16
    header(ws, C0 - 1, 2, ["Categoria", "Mês selecionado", "Ano", "% do mês", "aux"], height=30)
    header(ws, C0 - 1, 8, ["#", "Top 10 categorias do mês", "Valor"], height=30)
    for i in range(41):
        r = C0 + i
        rr = 33 + i
        ws[f"B{r}"].value = f"={q('res')}!A{rr}"
        ws[f"C{r}"].value = f"=INDEX({q('res')}!B{rr}:M{rr},dash_MesNum)"
        ws[f"D{r}"].value = f"={q('res')}!N{rr}"
        ws[f"E{r}"].value = f'=IF(SUM($C${C0}:$C${C0 + 40})=0,"",C{r}/SUM($C${C0}:$C${C0 + 40}))'
        ws[f"F{r}"].value = f"=C{r}+ROW()/1000000000"
        for col, fmt in zip("BCDEF", [None, BRL0, BRL0, PCT, "0.000"]):
            calc(ws[f"{col}{r}"], fmt)
    for n in range(1, 11):
        r = C0 + n - 1
        ws[f"H{r}"].value = n
        ws[f"J{r}"].value = f"=INDEX($C${C0}:$C${C0 + 40},MATCH(LARGE($F${C0}:$F${C0 + 40},H{r}),$F${C0}:$F${C0 + 40},0))"
        ws[f"I{r}"].value = f'=IF(J{r}<=0,"",INDEX($B${C0}:$B${C0 + 40},MATCH(LARGE($F${C0}:$F${C0 + 40},H{r}),$F${C0}:$F${C0 + 40},0)))'
        for col, fmt in zip("HIJ", ["0", None, BRL0]):
            calc(ws[f"{col}{r}"], fmt)
    # metas
    header(ws, C0 - 1, 12, ["Meta", "% realizado"], height=30)
    for i in range(10):
        r = C0 + i
        ws[f"L{r}"].value = f"=IF({q('meta')}!A{7 + i}=\"\",\"\",{q('meta')}!A{7 + i})"
        ws[f"M{r}"].value = f"=IF({q('meta')}!A{7 + i}=\"\",0,N({q('meta')}!H{7 + i}))"
        calc(ws[f"L{r}"])
        calc(ws[f"M{r}"], PCT)

    # ------------------------------------------------------------ gráficos
    def style_axes(ch):
        ch.x_axis.delete = False
        ch.y_axis.delete = False
        ch.legend.position = "b"
        ch.y_axis.majorGridlines = ch.y_axis.majorGridlines
        ch.width, ch.height = 16.5, 8.2

    cats = Reference(ws, min_col=2, min_row=B, max_row=B + 11)

    ch1 = BarChart()
    ch1.type, ch1.grouping, ch1.title = "col", "clustered", "Receitas × Despesas"
    for col, color in [(6, "2E8B57"), (9, CORAL)]:
        s = Series(Reference(ws, min_col=col, min_row=B - 1, max_row=B + 11), title_from_data=True)
        s.graphicalProperties.solidFill = color
        s.graphicalProperties.line.solidFill = color
        ch1.series.append(s)
    ch1.set_categories(cats)
    ch1.y_axis.numFmt = '"R$" #,##0'
    ch1.gapWidth = 60
    style_axes(ch1)
    ws.add_chart(ch1, "B19")

    ch2 = LineChart()
    ch2.title = "Saldo acumulado e patrimônio"
    for col, color in [(12, NAVY), (15, SKY), (13, "2E8B57")]:
        s = Series(Reference(ws, min_col=col, min_row=B - 1, max_row=B + 11), title_from_data=True)
        s.graphicalProperties.line.solidFill = color
        s.graphicalProperties.line.width = 28000
        s.smooth = False
        ch2.series.append(s)
    ch2.set_categories(cats)
    ch2.y_axis.numFmt = '"R$" #,##0'
    style_axes(ch2)
    ws.add_chart(ch2, "H19")

    ch3 = BarChart()
    ch3.type, ch3.title = "bar", "Top 10 gastos do mês"
    s = Series(Reference(ws, min_col=10, min_row=C0 - 1, max_row=C0 + 9), title_from_data=True)
    s.graphicalProperties.solidFill = CORAL
    s.graphicalProperties.line.solidFill = CORAL
    ch3.series.append(s)
    ch3.set_categories(Reference(ws, min_col=9, min_row=C0, max_row=C0 + 9))
    ch3.y_axis.numFmt = '"R$" #,##0'
    ch3.x_axis.scaling.orientation = "maxMin"
    ch3.gapWidth = 40
    style_axes(ch3)
    ch3.legend = None
    ws.add_chart(ch3, "B37")

    ch4 = BarChart()
    ch4.type, ch4.grouping, ch4.title = "col", "clustered", "Saldo do mês × categoria filtrada"
    for col, color in [(11, TEAL), (16, GOLD)]:
        s = Series(Reference(ws, min_col=col, min_row=B - 1, max_row=B + 11), title_from_data=True)
        s.graphicalProperties.solidFill = color
        s.graphicalProperties.line.solidFill = color
        ch4.series.append(s)
    ch4.set_categories(cats)
    ch4.y_axis.numFmt = '"R$" #,##0'
    style_axes(ch4)
    ch4.x_axis.tickLblPos = "low"
    ws.add_chart(ch4, "H37")

    ch5 = BarChart()
    ch5.type, ch5.title = "bar", "Metas — % realizado"
    s = Series(Reference(ws, min_col=13, min_row=C0 - 1, max_row=C0 + 9), title_from_data=True)
    s.graphicalProperties.solidFill = "2E8B57"
    s.graphicalProperties.line.solidFill = "2E8B57"
    ch5.series.append(s)
    ch5.set_categories(Reference(ws, min_col=12, min_row=C0, max_row=C0 + 9))
    ch5.y_axis.numFmt = "0%"
    ch5.y_axis.scaling.min = 0
    ch5.y_axis.scaling.max = 1
    ch5.x_axis.scaling.orientation = "maxMin"
    style_axes(ch5)
    ch5.legend = None
    ws.add_chart(ch5, "B55")

    ch6 = BarChart()
    ch6.type, ch6.grouping, ch6.title = "col", "clustered", "Comprometimento da renda"
    s = Series(Reference(ws, min_col=17, min_row=B - 1, max_row=B + 11), title_from_data=True)
    s.graphicalProperties.solidFill = GOLD
    s.graphicalProperties.line.solidFill = GOLD
    ch6.series.append(s)
    ch6.set_categories(cats)
    ch6.y_axis.numFmt = "0%"
    style_axes(ch6)
    ch6.legend = None
    ws.add_chart(ch6, "H55")
    ws.freeze_panes = "A5"


# ====================================================================== Início
def build_inicio(ws, ex):
    top(ws, "Planilha Financeira Pessoal", "Central de controle: receitas, despesas, cartões, contas fixas, orçamento, investimentos e metas — sem macros.",
        {"A": 3, "B": 30, "C": 90})
    ws["A1"].value = None
    ws["B1"].value = "Planilha Financeira Pessoal"
    ws["B1"].font = font(size=22, bold=True, color=NAVY)
    ws["A2"].value = None
    ws["B2"].value = "Central de controle: receitas, despesas, cartões, contas fixas, orçamento, investimentos e metas — sem macros."
    ws["B2"].font = font(size=10, italic=True, color=GRAY_TXT)
    r = 4
    if ex:
        ws[f"B{r}"].value = "ATENÇÃO: esta versão contém DADOS FICTÍCIOS de exemplo (marcados com '(exemplo)'). Use o arquivo '_em_branco' para começar do zero, ou apague o conteúdo das células creme."
        ws[f"B{r}"].font = font(bold=True, color=AMBER_TXT)
        ws[f"B{r}"].fill = fill(AMBER_BG)
        ws.merge_cells(f"B{r}:C{r}")
        r += 2

    section(ws, f"B{r}", "Navegação")
    r += 1
    abas = [
        ("dash", "Indicadores, gráficos e filtros por ano, mês e categoria."),
        ("rec", "Lançamentos de entradas (salário, extras, rendimentos resgatados...)."),
        ("desp", "Gastos pagos fora do cartão de crédito (Pix, débito, boleto, dinheiro)."),
        ("cc", "Cadastro de cartões, compras (à vista e parceladas) e faturas por mês."),
        ("fat", "Registro do pagamento das faturas (não entra como despesa)."),
        ("cf", "Contas recorrentes com status do mês: paga, vencida, vence em breve."),
        ("orc", "Planejado × realizado por categoria."),
        ("inv", "Carteira, aportes, resgates, rendimentos e evolução mensal."),
        ("meta", "Objetivos, prazos, % realizado e aporte mensal necessário."),
        ("res", "Consolidação dos 12 meses e comparativo entre anos."),
        ("cfg", "Saldo inicial, dias de alerta e listas (categorias, formas de pagamento...)."),
    ]
    for key, desc in abas:
        c = ws[f"B{r}"]
        c.value = f"→ {SH[key]}"
        c.hyperlink = f"#'{SH[key]}'!A1"
        c.font = font(bold=True, color=SKY, underline="single")
        ws[f"C{r}"].value = desc
        ws[f"C{r}"].font = font()
        r += 1

    r += 1
    section(ws, f"B{r}", "Legenda de cores")
    r += 1
    for sample, desc in [(inp, "Entrada manual — digite ou escolha na lista suspensa."),
                         (calc, "Fórmula automática — protegida contra alteração acidental."),
                         (None, "Indicador calculado em destaque.")]:
        cell = ws[f"B{r}"]
        cell.value = "R$ 1.234,56"
        if sample:
            sample(cell, BRL)
        else:
            calc(cell, BRL, bold=True, color=TEAL, bg=TEAL_L)
        cell.value = 1234.56
        ws[f"C{r}"].value = desc
        ws[f"C{r}"].font = font()
        r += 1
    for bg, fg, desc in [(RED_BG, RED_TXT, "Vermelho: vencido, acima do orçamento ou saldo negativo."),
                         (AMBER_BG, AMBER_TXT, "Âmbar: vence nos próximos dias (ajuste em Configurações) ou atenção (≥ 90% do orçamento)."),
                         (GREEN_BG, GREEN_TXT, "Verde: pago / concluído.")]:
        cell = ws[f"B{r}"]
        cell.value = "Status"
        cell.fill, cell.font, cell.border = fill(bg), font(bold=True, color=fg), BOX
        ws[f"C{r}"].value = desc
        ws[f"C{r}"].font = font()
        r += 1

    r += 1
    section(ws, f"B{r}", "Como usar (passo a passo)")
    r += 1
    passos = [
        ("1. Configurações", "Informe o saldo inicial em conta e revise categorias e formas de pagamento."),
        ("2. Cartões", "Cadastre cada cartão com limite, dia de FECHAMENTO e dia de VENCIMENTO."),
        ("3. Contas fixas", "Cadastre as despesas recorrentes (aluguel, luz, internet...) com dia de vencimento."),
        ("4. Orçamento", "Defina quanto pretende gastar por categoria em cada mês."),
        ("5. Dia a dia", "Lance receitas, despesas (fora do cartão) e compras no cartão. Uma compra parcelada é lançada UMA vez com o nº de parcelas."),
        ("6. Faturas", "Quando pagar uma fatura, registre na aba Faturas (cartão + mês + valor pago)."),
        ("7. Investimentos", "Registre aportes, resgates e, periodicamente, o rendimento (diferença de saldo informada pela instituição)."),
        ("8. Dashboard", "Escolha ano, mês e categoria para analisar."),
    ]
    for a, b in passos:
        ws[f"B{r}"].value = a
        ws[f"B{r}"].font = font(bold=True)
        ws[f"C{r}"].value = b
        ws[f"C{r}"].font = font()
        ws[f"C{r}"].alignment = Alignment(wrap_text=True, vertical="top")
        if len(b) > 95:
            ws.row_dimensions[r].height = 28
        r += 1

    r += 1
    section(ws, f"B{r}", "Regras para evitar duplicidade")
    r += 1
    regras = [
        "Compra no cartão de crédito: lance SOMENTE na aba Cartões de Crédito. Ela entra nas despesas no mês de vencimento de cada parcela.",
        "Pagamento da fatura: registre SOMENTE na aba Faturas. Ele NÃO é despesa (as compras já foram contadas) — apenas baixa a fatura e libera o limite.",
        "'Cartão de crédito' não existe como forma de pagamento em Despesas justamente para impedir lançamento em dobro.",
        "Conta fixa: o cadastro não gera despesa. Ao pagar, lance em Despesas e escolha a conta em 'Conta fixa vinculada' — o status muda para 'Paga'.",
        "Aportes em investimentos não são despesas: lance na aba Investimentos (reduzem o saldo em conta e aumentam o saldo investido).",
        "Compra feita no dia do fechamento ou depois entra na fatura seguinte. Parcelas atravessam meses e anos automaticamente.",
    ]
    for t in regras:
        ws[f"C{r}"].value = "• " + t
        ws[f"C{r}"].font = font()
        ws[f"C{r}"].alignment = Alignment(wrap_text=True, vertical="top")
        ws.row_dimensions[r].height = 28
        r += 1

    r += 1
    section(ws, f"B{r}", "Uso contínuo e manutenção")
    r += 1
    manut = [
        "Não é preciso criar abas por ano: todos os lançamentos ficam na mesma lista e o filtro de ANO do Dashboard muda Resumo, Contas fixas, Orçamento e gráficos.",
        "Capacidade pré-formatada: 2.000 receitas, 6.000 despesas, 4.000 compras no cartão, 1.000 faturas e 3.000 movimentações de investimento.",
        "As abas estão protegidas SEM senha (só para evitar apagar fórmulas). Para alterar a estrutura: Revisão > Desproteger Planilha.",
        "Para remover os exemplos: selecione as áreas creme de cada aba e pressione Delete (as fórmulas ficam intactas), ou use o arquivo em branco.",
        "Valores 'A receber' e despesas 'Pendente' já entram nos totais do mês (visão de compromissos). O Dashboard separa pago × pendente.",
    ]
    for t in manut:
        ws[f"C{r}"].value = "• " + t
        ws[f"C{r}"].font = font()
        ws[f"C{r}"].alignment = Alignment(wrap_text=True, vertical="top")
        ws.row_dimensions[r].height = 28
        r += 1


if __name__ == "__main__":
    out = os.path.dirname(os.path.abspath(__file__))
    build(os.path.join(out, "Planilha_Financeira_Pessoal.xlsx"), exemplos=True)
    build(os.path.join(out, "Planilha_Financeira_Pessoal_em_branco.xlsx"), exemplos=False)
    print("ok")
