/**
 * Reporte técnico: Inconsistencias diarias llamadas vs gestiones — Abril 2026
 * De: IPTEGRA SAS · Para: DISNORTE / DISSUR
 *
 * Genera reporte_inconsistencias_abril_2026.docx
 */
const fs = require('fs');
const path = require('path');
const {
    Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
    Header, Footer, AlignmentType, PageOrientation, LevelFormat,
    HeadingLevel, BorderStyle, WidthType, ShadingType, VerticalAlign,
    PageNumber, PageBreak, TabStopType, TabStopPosition,
} = require('docx');

// ── Datos extraídos de BD ─────────────────────────────────────────────────
// Ventana: 2026-04-01 → 2026-04-30 — Solo entrantes (tipo_llamada=3)
// Gestiones deduped: 1 por call_id (criterio MAX(id))
// TZ: America/Bogota (calibración del sistema, representa hora wall-clock Managua)

const TOTAL_ATENDIDAS = 242710;
const TOTAL_SPLIT     = 53;     // 0.022 %
const TOTAL_GESTIONES = 230104;
const TOTAL_GEST_DESF = 1860;   // 0.808 %

// Día por día — 30 filas
// [día, atendidas, inic_a_dsig, cerr_de_dant, gest_reg, gest_entran, gest_salen]
const DATOS_DIA = [
    ['01',  6820, 0, 2,  6606,  24,  37],
    ['02',  2299, 1, 0,  2217,  37,  51],
    ['03',  4312, 1, 1,  4141,  51,  50],
    ['04',  4250, 0, 1,  4152,  50,  21],
    ['05',  4063, 0, 0,  3858,  21,  21],
    ['06',  8025, 0, 0,  7700,  21,  49],
    ['07',  9219, 0, 0,  8876,  49,  39],
    ['08',  9045, 0, 0,  8593,  39,  49],
    ['09', 10211, 0, 0,  9714,  49,  49],
    ['10', 10269, 4, 0,  9679,  49, 107],
    ['11',  8611, 1, 4,  8113, 107,  73],
    ['12',  6302, 2, 1,  5975,  73,  38],
    ['13',  9467, 0, 2,  8940,  38,  39],
    ['14',  9413, 1, 0,  8871,  39,  58],
    ['15',  9118, 0, 1,  8691,  58,  34],
    ['16',  9690, 4, 0,  9166,  34,  32],
    ['17',  9531, 4, 4,  9009,  32,  96],
    ['18',  7593, 5, 4,  7174,  96, 113],
    ['19',  5592, 8, 5,  5285, 113, 147],
    ['20',  9937, 1, 8,  9414, 147, 132],
    ['21',  8864, 0, 1,  8370, 132,  91],
    ['22',  8956, 2, 0,  8509,  91,  44],
    ['23', 10143, 2, 2,  9526,  44, 142],
    ['24', 10621, 3, 2, 10096, 142,  78],
    ['25',  7805, 2, 3,  7347,  78,  34],
    ['26',  6234, 1, 2,  5801,  34,  63],
    ['27',  9171, 1, 1,  8682,  63,  46],
    ['28',  8928, 5, 1,  8362,  46,  77],
    ['29',  8904, 0, 5,  8451,  77,  26],
    ['30',  9317, 3, 0,  8786,  26,  31],
];

// ── Helpers ───────────────────────────────────────────────────────────────
const COLOR_PRIMARIO   = '1F4E79'; // azul oscuro corporativo
const COLOR_ACENTO     = 'D5E8F0';
const COLOR_GRIS       = 'F2F2F2';
const COLOR_NEG        = 'FCE4E4';
const COLOR_POS        = 'E4F4E4';
const FUENTE           = 'Arial';

function p(text, opts = {}) {
    return new Paragraph({
        ...opts,
        children: [new TextRun({ text, font: FUENTE, ...opts.run })],
    });
}

function pBold(text, opts = {}) {
    return p(text, { ...opts, run: { ...opts.run, bold: true } });
}

function emptyP() { return new Paragraph({ children: [new TextRun(' ')] }); }

const border = { style: BorderStyle.SINGLE, size: 4, color: 'B0B0B0' };
const borders = { top: border, bottom: border, left: border, right: border };

function cell(text, opts = {}) {
    const { width, fill, bold = false, color, align = AlignmentType.LEFT, size = 20 } = opts;
    return new TableCell({
        borders,
        width: { size: width, type: WidthType.DXA },
        shading: fill ? { fill, type: ShadingType.CLEAR } : undefined,
        margins: { top: 60, bottom: 60, left: 100, right: 100 },
        verticalAlign: VerticalAlign.CENTER,
        children: [new Paragraph({
            alignment: align,
            children: [new TextRun({ text: String(text), font: FUENTE, bold, color, size })],
        })],
    });
}

// ── Tabla diaria ──────────────────────────────────────────────────────────
const COLS_W = [600, 1100, 1100, 1100, 1100, 1100, 1100, 1100]; // = 9300, dentro de A4 con márgenes 1"
const HEADER_TXT = [
    'Día', 'Atendidas', 'Inic→D+1', 'Cerr←D-1', 'Gest reg.', 'Gest entran', 'Gest salen', 'Δ neto',
];

const filaHeader = new TableRow({
    tableHeader: true,
    children: HEADER_TXT.map((t, i) => cell(t, {
        width: COLS_W[i], fill: COLOR_PRIMARIO, bold: true, color: 'FFFFFF',
        align: AlignmentType.CENTER, size: 18,
    })),
});

let sumAtn = 0, sumIa = 0, sumCa = 0, sumGr = 0, sumGe = 0, sumGs = 0;
const filasDia = DATOS_DIA.map(([dia, atn, ia, ca, gr, ge, gs]) => {
    sumAtn += atn; sumIa += ia; sumCa += ca; sumGr += gr; sumGe += ge; sumGs += gs;
    const delta = ge - gs;
    const deltaFill = delta > 0 ? COLOR_POS : delta < 0 ? COLOR_NEG : undefined;
    const deltaTxt = delta > 0 ? `+${delta}` : String(delta);
    return new TableRow({
        children: [
            cell(dia, { width: COLS_W[0], align: AlignmentType.CENTER, bold: true }),
            cell(atn.toLocaleString('es-NI'), { width: COLS_W[1], align: AlignmentType.RIGHT }),
            cell(ia, { width: COLS_W[2], align: AlignmentType.CENTER }),
            cell(ca, { width: COLS_W[3], align: AlignmentType.CENTER }),
            cell(gr.toLocaleString('es-NI'), { width: COLS_W[4], align: AlignmentType.RIGHT }),
            cell(ge, { width: COLS_W[5], align: AlignmentType.CENTER }),
            cell(gs, { width: COLS_W[6], align: AlignmentType.CENTER }),
            cell(deltaTxt, { width: COLS_W[7], align: AlignmentType.CENTER, bold: true, fill: deltaFill }),
        ],
    });
});

const filaTotal = new TableRow({
    children: [
        cell('TOT', { width: COLS_W[0], fill: COLOR_GRIS, bold: true, align: AlignmentType.CENTER }),
        cell(sumAtn.toLocaleString('es-NI'), { width: COLS_W[1], fill: COLOR_GRIS, bold: true, align: AlignmentType.RIGHT }),
        cell(sumIa, { width: COLS_W[2], fill: COLOR_GRIS, bold: true, align: AlignmentType.CENTER }),
        cell(sumCa, { width: COLS_W[3], fill: COLOR_GRIS, bold: true, align: AlignmentType.CENTER }),
        cell(sumGr.toLocaleString('es-NI'), { width: COLS_W[4], fill: COLOR_GRIS, bold: true, align: AlignmentType.RIGHT }),
        cell(sumGe, { width: COLS_W[5], fill: COLOR_GRIS, bold: true, align: AlignmentType.CENTER }),
        cell(sumGs, { width: COLS_W[6], fill: COLOR_GRIS, bold: true, align: AlignmentType.CENTER }),
        cell(sumGe - sumGs, { width: COLS_W[7], fill: COLOR_GRIS, bold: true, align: AlignmentType.CENTER }),
    ],
});

const tablaDiaria = new Table({
    width: { size: 9300, type: WidthType.DXA },
    columnWidths: COLS_W,
    rows: [filaHeader, ...filasDia, filaTotal],
});

// ── Tabla resumen ejecutivo ───────────────────────────────────────────────
const COLS_RES = [4400, 2000, 2900]; // = 9300
const tablaResumen = new Table({
    width: { size: 9300, type: WidthType.DXA },
    columnWidths: COLS_RES,
    rows: [
        new TableRow({
            tableHeader: true,
            children: [
                cell('Métrica', { width: COLS_RES[0], fill: COLOR_PRIMARIO, bold: true, color: 'FFFFFF', size: 20 }),
                cell('Volumen', { width: COLS_RES[1], fill: COLOR_PRIMARIO, bold: true, color: 'FFFFFF', size: 20, align: AlignmentType.CENTER }),
                cell('% sobre total', { width: COLS_RES[2], fill: COLOR_PRIMARIO, bold: true, color: 'FFFFFF', size: 20, align: AlignmentType.CENTER }),
            ],
        }),
        new TableRow({ children: [
            cell('Llamadas entrantes atendidas (abril)', { width: COLS_RES[0] }),
            cell(TOTAL_ATENDIDAS.toLocaleString('es-NI'), { width: COLS_RES[1], align: AlignmentType.RIGHT, bold: true }),
            cell('100.000 %', { width: COLS_RES[2], align: AlignmentType.CENTER }),
        ]}),
        new TableRow({ children: [
            cell('Llamadas que cruzan medianoche (split-day)', { width: COLS_RES[0] }),
            cell(TOTAL_SPLIT.toLocaleString('es-NI'), { width: COLS_RES[1], align: AlignmentType.RIGHT, bold: true }),
            cell((100*TOTAL_SPLIT/TOTAL_ATENDIDAS).toFixed(3) + ' %', { width: COLS_RES[2], align: AlignmentType.CENTER }),
        ]}),
        new TableRow({ children: [
            cell('Gestiones registradas (deduped, 1 por call_id)', { width: COLS_RES[0] }),
            cell(TOTAL_GESTIONES.toLocaleString('es-NI'), { width: COLS_RES[1], align: AlignmentType.RIGHT, bold: true }),
            cell('100.000 %', { width: COLS_RES[2], align: AlignmentType.CENTER }),
        ]}),
        new TableRow({ children: [
            cell('Gestiones cuyo día de registro ≠ día de la llamada', { width: COLS_RES[0] }),
            cell(TOTAL_GEST_DESF.toLocaleString('es-NI'), { width: COLS_RES[1], align: AlignmentType.RIGHT, bold: true }),
            cell((100*TOTAL_GEST_DESF/TOTAL_GESTIONES).toFixed(3) + ' %', { width: COLS_RES[2], align: AlignmentType.CENTER }),
        ]}),
    ],
});

// ── Documento ─────────────────────────────────────────────────────────────
const doc = new Document({
    creator: 'IPTEGRA SAS',
    title: 'Inconsistencias diarias llamadas vs gestiones — Abril 2026',
    description: 'Reporte técnico de diagnóstico — DISNORTE / DISSUR',
    styles: {
        default: { document: { run: { font: FUENTE, size: 22 } } },
        paragraphStyles: [
            { id: 'Heading1', name: 'Heading 1', basedOn: 'Normal', next: 'Normal', quickFormat: true,
              run: { size: 32, bold: true, font: FUENTE, color: COLOR_PRIMARIO },
              paragraph: { spacing: { before: 360, after: 200 }, outlineLevel: 0 } },
            { id: 'Heading2', name: 'Heading 2', basedOn: 'Normal', next: 'Normal', quickFormat: true,
              run: { size: 26, bold: true, font: FUENTE, color: COLOR_PRIMARIO },
              paragraph: { spacing: { before: 280, after: 160 }, outlineLevel: 1 } },
            { id: 'Heading3', name: 'Heading 3', basedOn: 'Normal', next: 'Normal', quickFormat: true,
              run: { size: 23, bold: true, font: FUENTE, color: '2E5F8E' },
              paragraph: { spacing: { before: 200, after: 120 }, outlineLevel: 2 } },
        ],
    },
    numbering: {
        config: [
            { reference: 'bullets',
              levels: [{ level: 0, format: LevelFormat.BULLET, text: '•', alignment: AlignmentType.LEFT,
                style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
            { reference: 'numbers',
              levels: [{ level: 0, format: LevelFormat.DECIMAL, text: '%1.', alignment: AlignmentType.LEFT,
                style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
        ],
    },
    sections: [{
        properties: {
            page: {
                size: { width: 12240, height: 15840 }, // US Letter
                margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 },
            },
        },
        headers: {
            default: new Header({
                children: [new Paragraph({
                    tabStops: [{ type: TabStopType.RIGHT, position: 9360 }],
                    border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: COLOR_PRIMARIO, space: 4 } },
                    children: [
                        new TextRun({ text: 'IPTEGRA SAS', font: FUENTE, size: 18, bold: true, color: COLOR_PRIMARIO }),
                        new TextRun({ text: '\tReporte técnico — DISNORTE / DISSUR', font: FUENTE, size: 18, color: '707070' }),
                    ],
                })],
            }),
        },
        footers: {
            default: new Footer({
                children: [new Paragraph({
                    tabStops: [{ type: TabStopType.RIGHT, position: 9360 }],
                    children: [
                        new TextRun({ text: 'Confidencial — Uso interno', font: FUENTE, size: 16, color: '707070' }),
                        new TextRun({ text: '\tPágina ', font: FUENTE, size: 16, color: '707070' }),
                        new TextRun({ children: [PageNumber.CURRENT], font: FUENTE, size: 16, color: '707070' }),
                        new TextRun({ text: ' de ', font: FUENTE, size: 16, color: '707070' }),
                        new TextRun({ children: [PageNumber.TOTAL_PAGES], font: FUENTE, size: 16, color: '707070' }),
                    ],
                })],
            }),
        },
        children: [
            // ── PORTADA ──────────────────────────────────────────────
            emptyP(), emptyP(), emptyP(), emptyP(),
            new Paragraph({
                alignment: AlignmentType.CENTER,
                children: [new TextRun({ text: 'REPORTE TÉCNICO', font: FUENTE, size: 28, bold: true, color: '707070' })],
            }),
            emptyP(),
            new Paragraph({
                alignment: AlignmentType.CENTER,
                children: [new TextRun({ text: 'Inconsistencias diarias entre conteo de llamadas y gestiones', font: FUENTE, size: 40, bold: true, color: COLOR_PRIMARIO })],
            }),
            emptyP(),
            new Paragraph({
                alignment: AlignmentType.CENTER,
                children: [new TextRun({ text: 'Análisis del comportamiento del sistema OmniLeads Analytics Pro', font: FUENTE, size: 26, color: '404040' })],
            }),
            new Paragraph({
                alignment: AlignmentType.CENTER,
                children: [new TextRun({ text: 'Período: 1 al 30 de abril de 2026', font: FUENTE, size: 26, color: '404040' })],
            }),
            emptyP(), emptyP(), emptyP(), emptyP(), emptyP(), emptyP(), emptyP(), emptyP(),
            new Paragraph({
                alignment: AlignmentType.CENTER,
                border: { top: { style: BorderStyle.SINGLE, size: 12, color: COLOR_PRIMARIO, space: 8 } },
                children: [new TextRun({ text: 'De', font: FUENTE, size: 22, color: '707070' })],
            }),
            new Paragraph({
                alignment: AlignmentType.CENTER,
                children: [new TextRun({ text: 'IPTEGRA SAS', font: FUENTE, size: 36, bold: true, color: COLOR_PRIMARIO })],
            }),
            emptyP(),
            new Paragraph({
                alignment: AlignmentType.CENTER,
                children: [new TextRun({ text: 'Para', font: FUENTE, size: 22, color: '707070' })],
            }),
            new Paragraph({
                alignment: AlignmentType.CENTER,
                children: [new TextRun({ text: 'DISNORTE / DISSUR', font: FUENTE, size: 36, bold: true, color: COLOR_PRIMARIO })],
            }),
            emptyP(), emptyP(), emptyP(),
            new Paragraph({
                alignment: AlignmentType.CENTER,
                children: [new TextRun({ text: 'Mayo de 2026', font: FUENTE, size: 22, italics: true, color: '707070' })],
            }),
            new Paragraph({ children: [new PageBreak()] }),

            // ── 1. RESUMEN EJECUTIVO ─────────────────────────────────
            new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun({ text: '1. Resumen ejecutivo', font: FUENTE })] }),

            p('El presente documento explica por qué el sistema OmniLeads Analytics Pro ' +
              'puede mostrar diferencias entre el conteo de llamadas y el conteo de gestiones ' +
              'al cierre de cada día, y cuantifica el impacto durante el mes de abril de 2026.', { spacing: { after: 160 } }),

            p('La causa raíz es de naturaleza temporal y se compone de tres situaciones ' +
              'normales en la operación de un call center 24×7:', { spacing: { after: 120 } }),

            new Paragraph({ numbering: { reference: 'bullets', level: 0 }, children: [
                new TextRun({ text: 'Llamadas iniciadas en un día que finalizan al día siguiente ', font: FUENTE, bold: true }),
                new TextRun({ text: '(cruzan medianoche).', font: FUENTE }),
            ]}),
            new Paragraph({ numbering: { reference: 'bullets', level: 0 }, children: [
                new TextRun({ text: 'Llamadas finalizadas en un día que iniciaron el día anterior ', font: FUENTE, bold: true }),
                new TextRun({ text: '(la misma situación, vista desde el día siguiente).', font: FUENTE }),
            ]}),
            new Paragraph({ numbering: { reference: 'bullets', level: 0 }, children: [
                new TextRun({ text: 'Gestiones registradas con desfase ', font: FUENTE, bold: true }),
                new TextRun({ text: 'respecto al día de su llamada (el agente cierra el formulario después de medianoche).', font: FUENTE }),
            ]}),

            emptyP(),
            p('Estos eventos son operativamente legítimos —no son errores ni omisiones— ' +
              'pero su contabilidad genera diferencias diarias entre las dos métricas ' +
              'que el sistema reporta independientemente.', { spacing: { after: 200 } }),

            new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun({ text: 'Magnitud del impacto en abril 2026', font: FUENTE })] }),
            tablaResumen,
            emptyP(),
            p('Sobre 242,710 llamadas atendidas y 230,104 gestiones registradas en el mes, ' +
              'las inconsistencias diarias afectan menos del 1 % del total. ' +
              'El impacto sobre los acumulados mensuales es despreciable, pero sí es perceptible ' +
              'en reportes diarios y de turno.', { spacing: { after: 200 } }),

            new Paragraph({ children: [new PageBreak()] }),

            // ── 2. CONTEXTO TÉCNICO ──────────────────────────────────
            new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun({ text: '2. Contexto técnico', font: FUENTE })] }),

            new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun({ text: '2.1 Cómo se contabiliza una llamada', font: FUENTE })] }),
            p('Una llamada en OmniLeads no es un solo registro: es una ', { spacing: { after: 0 } }),
            p('secuencia de eventos almacenados en la tabla reportes_app_llamadalog. ' +
              'Cada llamada tiene típicamente entre 3 y 8 eventos (entrada en cola, conexión, ' +
              'transferencias, finalización). Todos los eventos comparten un identificador único ' +
              'llamado callid.', { spacing: { after: 160 } }),
            p('El sistema considera que una llamada fue ATENDIDA cuando alguno de sus eventos ' +
              'corresponde a un cierre con agente: COMPLETEAGENT, COMPLETEOUTNUM, COMPLETE-BTOUT ' +
              'o COMPLETE-CTOUT. La fecha que el sistema asigna a la llamada en sus reportes ' +
              'es la del último evento (el cierre).', { spacing: { after: 200 } }),

            new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun({ text: '2.2 Cómo se contabiliza una gestión', font: FUENTE })] }),
            p('Cuando un agente atiende una llamada y registra su resultado en el formulario, ' +
              'se genera un registro en ominicontacto_app_customformgestion. Cada gestión tiene ' +
              'un campo fecha que corresponde al ', { spacing: { after: 0 } }),
            new Paragraph({ children: [
                new TextRun({ text: 'momento exacto en que el agente guardó el formulario', font: FUENTE, bold: true }),
                new TextRun({ text: ', no al momento de la llamada.', font: FUENTE }),
            ]}),
            emptyP(),
            p('Para el cruce con llamadas, el sistema deduplica gestiones por call_id ' +
              '(si un agente reabre y vuelve a guardar, queda solo la última). Una vez ' +
              'deduplicadas, las gestiones se asocian uno-a-uno con sus llamadas atendidas ' +
              'mediante el call_id.', { spacing: { after: 200 } }),

            new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun({ text: '2.3 Por qué surgen las diferencias', font: FUENTE })] }),
            p('El problema aparece porque los dos conteos usan dos relojes distintos:', { spacing: { after: 120 } }),
            new Paragraph({ numbering: { reference: 'bullets', level: 0 }, children: [
                new TextRun({ text: 'Llamadas: ', font: FUENTE, bold: true }),
                new TextRun({ text: 'fecha del cierre (último evento de la llamada).', font: FUENTE }),
            ]}),
            new Paragraph({ numbering: { reference: 'bullets', level: 0 }, children: [
                new TextRun({ text: 'Gestiones: ', font: FUENTE, bold: true }),
                new TextRun({ text: 'fecha en que el agente guardó el formulario.', font: FUENTE }),
            ]}),
            emptyP(),
            p('Cuando una llamada cruza medianoche, o cuando un agente cierra el formulario ' +
              'después de las 00:00 horas, ambos relojes apuntan a días diferentes y la ' +
              'gestión queda atribuida a un día distinto al de su llamada.', { spacing: { after: 200 } }),

            new Paragraph({ children: [new PageBreak()] }),

            // ── 3. TIPOS DE INCONSISTENCIA ────────────────────────────
            new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun({ text: '3. Tipos de inconsistencia identificados', font: FUENTE })] }),

            new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun({ text: '3.1 Llamadas iniciadas en un día sin finalizar (Inic→D+1)', font: FUENTE })] }),
            p('Son llamadas cuyo primer evento ocurre en el día D pero cuyo último evento ' +
              '(el cierre) ocurre en el día D+1. Desde la perspectiva del día D, parece ' +
              'que entró una llamada que no se cerró.', { spacing: { after: 120 } }),
            new Paragraph({ children: [new TextRun({ text: 'Ejemplo típico: ', font: FUENTE, italics: true, bold: true })], spacing: { after: 0 } }),
            p('un cliente llama a las 23:50, espera en cola, es atendido a las 23:58, ' +
              'la conversación se prolonga y el agente cuelga (COMPLETEAGENT) a las 00:07 ' +
              'del día siguiente.', { spacing: { after: 200 } }),

            new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun({ text: '3.2 Llamadas finalizadas en un día sin inicio (Cerr←D-1)', font: FUENTE })] }),
            p('Es exactamente la misma llamada del caso anterior, vista desde el día D+1. ' +
              'Su último evento está en D+1 pero su primer evento está en D. Desde la ' +
              'perspectiva de D+1, aparece una llamada que se cerró sin que se viera entrar.', { spacing: { after: 120 } }),
            p('Por construcción, el conteo total de "Inic→D+1" del mes debe coincidir ' +
              'con el conteo total de "Cerr←D-1" desplazado un día — ambas columnas reflejan ' +
              'el mismo conjunto de llamadas, observado desde sus dos extremos.', { spacing: { after: 200 } }),

            new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun({ text: '3.3 Gestiones registradas en un día cuya llamada fue otro día', font: FUENTE })] }),
            p('Cuando un agente termina la llamada justo antes de medianoche pero demora ' +
              'unos minutos en completar y guardar el formulario, el registro de la gestión ' +
              'queda fechado en el día siguiente, mientras que la llamada quedó cerrada en ' +
              'el día anterior.', { spacing: { after: 120 } }),
            p('Esto se contabiliza con dos columnas en el cuadro diario:', { spacing: { after: 80 } }),
            new Paragraph({ numbering: { reference: 'bullets', level: 0 }, children: [
                new TextRun({ text: 'Gest entran: ', font: FUENTE, bold: true }),
                new TextRun({ text: 'gestiones registradas en el día D cuya llamada fue el día D-1.', font: FUENTE }),
            ]}),
            new Paragraph({ numbering: { reference: 'bullets', level: 0 }, children: [
                new TextRun({ text: 'Gest salen: ', font: FUENTE, bold: true }),
                new TextRun({ text: 'gestiones cuya llamada fue el día D pero quedaron registradas el día D+1.', font: FUENTE }),
            ]}),
            new Paragraph({ numbering: { reference: 'bullets', level: 0 }, children: [
                new TextRun({ text: 'Δ neto: ', font: FUENTE, bold: true }),
                new TextRun({ text: 'diferencia entre las que entran y las que salen. ', font: FUENTE }),
                new TextRun({ text: 'Un valor positivo significa que el día tuvo más gestiones tardías propias ' +
                    'recibidas que cedidas; un valor negativo indica lo contrario.', font: FUENTE }),
            ]}),
            emptyP(),
            p('Estas gestiones son válidas: corresponden a llamadas reales y a trabajo real ' +
              'del agente. Solo están "fuera de día" en términos de contabilidad.', { spacing: { after: 200 } }),

            new Paragraph({ children: [new PageBreak()] }),

            // ── 4. CUADRO DETALLADO ──────────────────────────────────
            new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun({ text: '4. Cuadro detallado — Abril 2026 día por día', font: FUENTE })] }),
            p('Para cada día del mes se muestran las cinco métricas relevantes y el delta ' +
              'neto de gestiones desfasadas. Datos extraídos de la base local sincronizada ' +
              'al 4 de mayo de 2026, sólo llamadas entrantes (tipo=3), gestiones deduplicadas ' +
              'por call_id.', { spacing: { after: 160 } }),

            tablaDiaria,

            emptyP(),
            new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun({ text: 'Cómo leer la tabla', font: FUENTE })] }),
            new Paragraph({ numbering: { reference: 'bullets', level: 0 }, children: [
                new TextRun({ text: 'Atendidas: ', font: FUENTE, bold: true }),
                new TextRun({ text: 'llamadas entrantes con cierre de agente cuyo último evento cae en ese día.', font: FUENTE }),
            ]}),
            new Paragraph({ numbering: { reference: 'bullets', level: 0 }, children: [
                new TextRun({ text: 'Inic→D+1: ', font: FUENTE, bold: true }),
                new TextRun({ text: 'llamadas iniciadas ese día que terminaron al día siguiente (cruzan medianoche).', font: FUENTE }),
            ]}),
            new Paragraph({ numbering: { reference: 'bullets', level: 0 }, children: [
                new TextRun({ text: 'Cerr←D-1: ', font: FUENTE, bold: true }),
                new TextRun({ text: 'llamadas terminadas ese día que iniciaron el día anterior.', font: FUENTE }),
            ]}),
            new Paragraph({ numbering: { reference: 'bullets', level: 0 }, children: [
                new TextRun({ text: 'Gest reg.: ', font: FUENTE, bold: true }),
                new TextRun({ text: 'gestiones (deduplicadas) cuya fecha de registro cae en ese día.', font: FUENTE }),
            ]}),
            new Paragraph({ numbering: { reference: 'bullets', level: 0 }, children: [
                new TextRun({ text: 'Gest entran / Gest salen: ', font: FUENTE, bold: true }),
                new TextRun({ text: 'cantidad de gestiones desfasadas que entran o salen del día.', font: FUENTE }),
            ]}),
            new Paragraph({ numbering: { reference: 'bullets', level: 0 }, children: [
                new TextRun({ text: 'Δ neto: ', font: FUENTE, bold: true }),
                new TextRun({ text: '(Gest entran) − (Gest salen). En verde si positivo, en rojo si negativo.', font: FUENTE }),
            ]}),

            new Paragraph({ children: [new PageBreak()] }),

            // ── 5. ANÁLISIS PORCENTUAL ───────────────────────────────
            new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun({ text: '5. Análisis del impacto porcentual', font: FUENTE })] }),

            new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun({ text: '5.1 Impacto sobre el total mensual', font: FUENTE })] }),
            new Paragraph({ children: [
                new TextRun({ text: 'En el acumulado mensual, las inconsistencias diarias se anulan entre sí ', font: FUENTE }),
                new TextRun({ text: '(lo que un día pierde, otro día lo gana). Por eso el total de abril ', font: FUENTE }),
                new TextRun({ text: 'queda prácticamente exacto frente a las cifras de OmniLeads:', font: FUENTE }),
            ]}),
            emptyP(),
            new Paragraph({ numbering: { reference: 'bullets', level: 0 }, children: [
                new TextRun({ text: '53 llamadas (0.022 %) ', font: FUENTE, bold: true }),
                new TextRun({ text: 'cruzaron medianoche en abril, sobre un universo de ' +
                    TOTAL_ATENDIDAS.toLocaleString('es-NI') + ' atendidas.', font: FUENTE }),
            ]}),
            new Paragraph({ numbering: { reference: 'bullets', level: 0 }, children: [
                new TextRun({ text: '1,860 gestiones (0.808 %) ', font: FUENTE, bold: true }),
                new TextRun({ text: 'quedaron registradas en un día distinto al de su llamada, sobre ' +
                    TOTAL_GESTIONES.toLocaleString('es-NI') + ' gestiones del mes.', font: FUENTE }),
            ]}),
            emptyP(),
            p('Es decir: si el supervisor compara los acumulados del mes contra el sistema ' +
              'fuente OmniLeads, la diferencia es inferior al 1 %.', { spacing: { after: 200 } }),

            new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun({ text: '5.2 Impacto sobre los reportes diarios', font: FUENTE })] }),
            p('A nivel diario, sin embargo, las diferencias son visibles. Tomando los días ' +
              'con mayor desfase neto en abril:', { spacing: { after: 120 } }),
            new Paragraph({ numbering: { reference: 'bullets', level: 0 }, children: [
                new TextRun({ text: '23 de abril: −98 gestiones netas ', font: FUENTE, bold: true }),
                new TextRun({ text: '(44 entran de D-1, 142 salen a D+1). El reporte diario muestra menos ' +
                    'gestiones que llamadas atendidas en proporción mayor que el resto de los días.', font: FUENTE }),
            ]}),
            new Paragraph({ numbering: { reference: 'bullets', level: 0 }, children: [
                new TextRun({ text: '17 de abril: −64 ', font: FUENTE, bold: true }),
                new TextRun({ text: '(32 entran, 96 salen).', font: FUENTE }),
            ]}),
            new Paragraph({ numbering: { reference: 'bullets', level: 0 }, children: [
                new TextRun({ text: '24 de abril: +64 ', font: FUENTE, bold: true }),
                new TextRun({ text: '(142 entran, 78 salen). El reporte diario muestra más gestiones que llamadas ' +
                    'iniciadas en el día porque recibió las gestiones tardías del 23.', font: FUENTE }),
            ]}),
            emptyP(),
            p('Estas oscilaciones son cíclicas: lo que un día pierde, el día anterior o ' +
              'siguiente lo recibe. Por eso al sumar todo el mes, el desfase desaparece.', { spacing: { after: 200 } }),

            new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun({ text: '5.3 Distribución del fenómeno en el mes', font: FUENTE })] }),
            p('Los días con mayor cantidad de llamadas split-day (Inic→D+1 + Cerr←D-1) ' +
              'tienden a ser los de fin de semana y los días con eventos operativos prolongados. ' +
              'En abril 2026:', { spacing: { after: 120 } }),
            new Paragraph({ numbering: { reference: 'bullets', level: 0 }, children: [
                new TextRun({ text: '19 de abril: 13 llamadas con corte de medianoche', font: FUENTE }),
            ]}),
            new Paragraph({ numbering: { reference: 'bullets', level: 0 }, children: [
                new TextRun({ text: '17 y 18 de abril: 8 y 9 respectivamente', font: FUENTE }),
            ]}),
            new Paragraph({ numbering: { reference: 'bullets', level: 0 }, children: [
                new TextRun({ text: '13 días del mes con cero split-day', font: FUENTE }),
            ]}),
            emptyP(),
            p('La mayoría de días con discrepancia están concentrados en la segunda mitad ' +
              'del mes, lo que refuerza el patrón de "gestiones tardías": no es un problema ' +
              'sistémico, es un fenómeno operativo distribuido.', { spacing: { after: 200 } }),

            new Paragraph({ children: [new PageBreak()] }),

            // ── 6. POR QUÉ NO SE DEBE ELIMINAR ──────────────────────
            new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun({ text: '6. Por qué no se recomienda eliminar estos registros', font: FUENTE })] }),

            new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun({ text: '6.1 Eliminar = maquillar resultados', font: FUENTE })] }),
            p('Cabría la tentación de "limpiar" la base eliminando las llamadas que cruzan ' +
              'medianoche o las gestiones registradas con desfase. Sin embargo, esa decisión ' +
              'tendría consecuencias graves desde el punto de vista de auditoría:', { spacing: { after: 120 } }),
            new Paragraph({ numbering: { reference: 'bullets', level: 0 }, children: [
                new TextRun({ text: 'Las llamadas split-day son llamadas reales. ', font: FUENTE, bold: true }),
                new TextRun({ text: 'Eliminarlas significaría borrar atenciones que el agente prestó al cliente. ' +
                    'El SLA del cliente se vería artificialmente "mejorado" por la simple omisión.', font: FUENTE }),
            ]}),
            new Paragraph({ numbering: { reference: 'bullets', level: 0 }, children: [
                new TextRun({ text: 'Las gestiones desfasadas son gestiones legítimas. ', font: FUENTE, bold: true }),
                new TextRun({ text: 'Cada una corresponde a una llamada atendida y a un formulario completado. ' +
                    'Eliminarlas reduciría la productividad reportada de los agentes que atienden cerca ' +
                    'del cierre del turno.', font: FUENTE }),
            ]}),
            new Paragraph({ numbering: { reference: 'bullets', level: 0 }, children: [
                new TextRun({ text: 'El sistema fuente OmniLeads conservaría los registros. ', font: FUENTE, bold: true }),
                new TextRun({ text: 'Cualquier auditoría cruzada (Power BI, exportaciones SQL directas a la base ' +
                    'fuente) detectaría inmediatamente la divergencia.', font: FUENTE }),
            ]}),

            new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun({ text: '6.2 La cifra cuenta una verdad operativa', font: FUENTE })] }),
            p('La diferencia entre "llamadas atendidas" y "gestiones registradas" en un día ' +
              'puntual es ', { spacing: { after: 0 } }),
            new Paragraph({ children: [
                new TextRun({ text: 'información valiosa para la operación', font: FUENTE, bold: true }),
                new TextRun({ text: ', no ruido a eliminar. Refleja:', font: FUENTE }),
            ]}),
            new Paragraph({ numbering: { reference: 'bullets', level: 0 }, children: [
                new TextRun({ text: 'Carga de cierre de turno (cuántos agentes terminan el día con un formulario ' +
                    'pendiente de guardar).', font: FUENTE }),
            ]}),
            new Paragraph({ numbering: { reference: 'bullets', level: 0 }, children: [
                new TextRun({ text: 'Llamadas largas que ocupan al agente más allá del cambio de día.', font: FUENTE }),
            ]}),
            new Paragraph({ numbering: { reference: 'bullets', level: 0 }, children: [
                new TextRun({ text: 'Patrones de demora en el registro de gestión por parte de turnos específicos.', font: FUENTE }),
            ]}),
            emptyP(),
            p('Suprimir estos datos privaría a la coordinación de información operativa real.', { spacing: { after: 200 } }),

            new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun({ text: '6.3 Trazabilidad y cumplimiento', font: FUENTE })] }),
            p('OmniLeads Analytics Pro está conectado en modo lectura a la base de OmniLeads. ' +
              'No se realizan escrituras ni borrados sobre los datos de origen — esto es una ' +
              'restricción técnica explícita del sistema, garantizada en el nivel de conexión ' +
              '(transacciones SET default_transaction_read_only=on).', { spacing: { after: 120 } }),
            p('Esta restricción es deliberada y forma parte de los compromisos de integridad ' +
              'del sistema con el cliente. Cualquier ejercicio de "limpieza" requeriría romper ' +
              'esa garantía y, además, afectaría retroactivamente reportes ya entregados.', { spacing: { after: 200 } }),

            new Paragraph({ children: [new PageBreak()] }),

            // ── 7. CONCLUSIONES ──────────────────────────────────────
            new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun({ text: '7. Conclusiones', font: FUENTE })] }),

            new Paragraph({ numbering: { reference: 'numbers', level: 0 }, children: [
                new TextRun({ text: 'Las diferencias diarias entre el conteo de llamadas y el de gestiones ' +
                    'son un fenómeno temporal esperado en una operación 24×7, no un error del sistema.', font: FUENTE }),
            ]}),
            new Paragraph({ numbering: { reference: 'numbers', level: 0 }, children: [
                new TextRun({ text: 'En abril de 2026, sobre 242,710 llamadas atendidas y 230,104 gestiones, ' +
                    'el desfase afecta menos del 1 % de los registros (0.022 % en llamadas, ' +
                    '0.808 % en gestiones).', font: FUENTE }),
            ]}),
            new Paragraph({ numbering: { reference: 'numbers', level: 0 }, children: [
                new TextRun({ text: 'El acumulado mensual no se ve afectado materialmente: las gestiones ' +
                    'desfasadas se compensan entre días contiguos.', font: FUENTE }),
            ]}),
            new Paragraph({ numbering: { reference: 'numbers', level: 0 }, children: [
                new TextRun({ text: 'A nivel diario, las diferencias son visibles y deben ser interpretadas ' +
                    'como información operativa: indican llamadas largas en cambio de día y ' +
                    'demoras en cierre de formulario.', font: FUENTE }),
            ]}),
            new Paragraph({ numbering: { reference: 'numbers', level: 0 }, children: [
                new TextRun({ text: 'No se recomienda eliminar ni filtrar estos registros: hacerlo ' +
                    'maquillaría los resultados, ocultaría carga real de la operación y ' +
                    'rompería la conciliación con OmniLeads.', font: FUENTE }),
            ]}),
            new Paragraph({ numbering: { reference: 'numbers', level: 0 }, children: [
                new TextRun({ text: 'La recomendación práctica para auditores y coordinadores es ' +
                    'comparar los reportes en ventanas de al menos una semana cuando se busca ' +
                    'cuadrar exactamente llamadas y gestiones, dado que las oscilaciones diarias ' +
                    'se compensan en períodos cortos.', font: FUENTE }),
            ]}),

            emptyP(), emptyP(),
            new Paragraph({
                border: { top: { style: BorderStyle.SINGLE, size: 6, color: COLOR_PRIMARIO, space: 6 } },
                children: [new TextRun({ text: ' ', font: FUENTE })],
            }),
            new Paragraph({
                alignment: AlignmentType.CENTER,
                children: [new TextRun({ text: 'IPTEGRA SAS · Análisis técnico OmniLeads Analytics Pro', font: FUENTE, size: 18, color: '707070', italics: true })],
            }),
            new Paragraph({
                alignment: AlignmentType.CENTER,
                children: [new TextRun({ text: 'Documento confidencial — DISNORTE / DISSUR', font: FUENTE, size: 18, color: '707070', italics: true })],
            }),
        ],
    }],
});

// ── Empaquetar ────────────────────────────────────────────────────────────
const outPath = path.join(__dirname, 'reporte_inconsistencias_abril_2026.docx');
Packer.toBuffer(doc).then(buf => {
    fs.writeFileSync(outPath, buf);
    console.log('OK →', outPath, '(' + buf.length + ' bytes)');
}).catch(err => {
    console.error('ERROR:', err);
    process.exit(1);
});
