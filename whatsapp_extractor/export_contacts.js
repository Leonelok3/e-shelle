const fs = require("fs");
const path = require("path");
const xlsx = require("xlsx");
const { parse } = require("csv-parse/sync");

const OUTPUT_DIR = path.join(__dirname, "exports");
const COLUMNS = ["nom", "numero", "ville", "groupe", "source", "consentement_confirme", "note"];

function ensureOutputDir() {
  if (!fs.existsSync(OUTPUT_DIR)) {
    fs.mkdirSync(OUTPUT_DIR, { recursive: true });
  }
}

function clean(value) {
  return String(value || "").trim();
}

function normalizePhone(value) {
  return clean(value).replace(/[()\s.-]/g, "");
}

function csvEscape(value) {
  const text = clean(value);
  if (/[",\n\r]/.test(text)) {
    return `"${text.replace(/"/g, '""')}"`;
  }
  return text;
}

function readRows(filePath) {
  const ext = path.extname(filePath).toLowerCase();
  if (ext === ".xlsx" || ext === ".xls") {
    const workbook = xlsx.readFile(filePath);
    const sheetName = workbook.SheetNames[0];
    return xlsx.utils.sheet_to_json(workbook.Sheets[sheetName], { defval: "" });
  }

  const raw = fs.readFileSync(filePath, "utf8");
  return parse(raw, {
    columns: true,
    bom: true,
    skip_empty_lines: true,
    trim: true,
  });
}

function pick(row, names) {
  for (const name of names) {
    if (row[name] !== undefined && row[name] !== "") {
      return row[name];
    }
  }
  return "";
}

async function prepareContactsFile(sourceFile) {
  if (!sourceFile) {
    throw new Error("Chemin du fichier source obligatoire.");
  }
  if (!fs.existsSync(sourceFile)) {
    throw new Error(`Fichier introuvable: ${sourceFile}`);
  }

  ensureOutputDir();
  const rows = readRows(sourceFile);
  const seen = new Set();
  const contacts = [];

  for (const row of rows) {
    const numero = normalizePhone(pick(row, ["numero", "phone", "telephone", "whatsapp", "tel"]));
    if (!numero || seen.has(numero)) {
      continue;
    }
    seen.add(numero);
    contacts.push({
      nom: clean(pick(row, ["nom", "name", "prenom", "client"])),
      numero,
      ville: clean(pick(row, ["ville", "city"])),
      groupe: clean(pick(row, ["groupe", "group", "source_groupe"])),
      source: "csv",
      consentement_confirme: "oui",
      note: clean(pick(row, ["note", "commentaire", "comment"])),
    });
  }

  const stamp = new Date().toISOString().replace(/[:.]/g, "-");
  const output = path.join(OUTPUT_DIR, `contacts-whatsapp-${stamp}.csv`);
  const lines = [COLUMNS.join(",")];
  for (const contact of contacts) {
    lines.push(COLUMNS.map((column) => csvEscape(contact[column])).join(","));
  }
  fs.writeFileSync(output, `${lines.join("\n")}\n`, "utf8");
  console.log(`${contacts.length} contact(s) prepares.`);
  return output;
}

if (require.main === module) {
  prepareContactsFile(process.argv[2])
    .then((output) => console.log(output))
    .catch((error) => {
      console.error(error.message);
      process.exit(1);
    });
}

module.exports = { prepareContactsFile };
