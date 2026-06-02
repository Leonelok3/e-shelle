require("dotenv").config();

const fs = require("fs");
const path = require("path");
const axios = require("axios");
const { parse } = require("csv-parse/sync");

function requireConsent() {
  const value = String(process.env.WHATSAPP_IMPORT_CONSENT || "").toLowerCase();
  if (!["oui", "yes", "true", "1"].includes(value)) {
    throw new Error(
      "Import bloque. Mets WHATSAPP_IMPORT_CONSENT=oui dans .env seulement si ces contacts ont autorise la communication."
    );
  }
}

function resolveInputFile(filePath) {
  if (filePath) {
    return filePath;
  }
  if (process.env.WHATSAPP_CONTACTS_FILE) {
    return process.env.WHATSAPP_CONTACTS_FILE;
  }
  const exportsDir = path.join(__dirname, "exports");
  if (!fs.existsSync(exportsDir)) {
    throw new Error("Aucun fichier fourni et dossier exports introuvable.");
  }
  const files = fs
    .readdirSync(exportsDir)
    .filter((name) => name.endsWith(".csv"))
    .map((name) => path.join(exportsDir, name))
    .sort((a, b) => fs.statSync(b).mtimeMs - fs.statSync(a).mtimeMs);
  if (!files.length) {
    throw new Error("Aucun CSV trouve dans whatsapp_extractor/exports.");
  }
  return files[0];
}

function readCsv(filePath) {
  if (!fs.existsSync(filePath)) {
    throw new Error(`Fichier introuvable: ${filePath}`);
  }
  const raw = fs.readFileSync(filePath, "utf8");
  return parse(raw, {
    columns: true,
    bom: true,
    skip_empty_lines: true,
    trim: true,
  });
}

async function importContactsToEshelle(filePath) {
  requireConsent();
  const input = resolveInputFile(filePath);
  const baseUrl = String(process.env.ESHELLE_API_BASE_URL || "http://127.0.0.1:8025").replace(/\/$/, "");
  const token = process.env.ESHELLE_API_TOKEN;
  if (!token) {
    throw new Error("ESHELLE_API_TOKEN est obligatoire dans .env.");
  }

  const rows = readCsv(input);
  let created = 0;
  let updated = 0;
  let failed = 0;

  for (const row of rows) {
    try {
      const response = await axios.post(
        `${baseUrl}/whatsapp/api/import-contact/`,
        {
          nom: row.nom || row.name || "",
          numero: row.numero || row.phone || row.telephone || row.whatsapp || "",
          ville: row.ville || row.city || "",
          groupe: row.groupe || row.group || "",
          source: row.source || "csv",
          consentement_confirme: true,
          note: row.note || "",
        },
        {
          headers: {
            Authorization: `Token ${token}`,
            "Content-Type": "application/json",
          },
          timeout: 15000,
        }
      );
      if (response.data.status === "created") {
        created += 1;
      } else {
        updated += 1;
      }
    } catch (error) {
      failed += 1;
      const details = error.response ? JSON.stringify(error.response.data) : error.message;
      console.error(`Echec import ${row.numero || row.phone || "sans numero"}: ${details}`);
    }
  }

  console.log(`Import termine. Crees: ${created}, existants/mis a jour: ${updated}, echecs: ${failed}`);
  return { created, updated, failed };
}

if (require.main === module) {
  importContactsToEshelle(process.argv[2])
    .catch((error) => {
      console.error(error.message);
      process.exit(1);
    });
}

module.exports = { importContactsToEshelle };
