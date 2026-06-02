const readline = require("readline");
const { prepareContactsFile } = require("./export_contacts");
const { importContactsToEshelle } = require("./import_to_eshelle");

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout,
});

function ask(question) {
  return new Promise((resolve) => rl.question(question, resolve));
}

async function main() {
  console.log("\nE-Shelle - Import Contacts WhatsApp autorises\n");
  console.log("1. Preparer un fichier CSV depuis CSV/Excel source");
  console.log("2. Importer les contacts vers Django");
  console.log("3. Preparer puis importer");
  console.log("4. Quitter\n");

  const choice = (await ask("Choix: ")).trim();
  try {
    if (choice === "1") {
      const file = await ask("Chemin du fichier CSV/Excel source: ");
      const output = await prepareContactsFile(file.trim());
      console.log(`Fichier prepare: ${output}`);
    } else if (choice === "2") {
      const file = await ask("Chemin du fichier CSV prepare: ");
      await importContactsToEshelle(file.trim());
    } else if (choice === "3") {
      const source = await ask("Chemin du fichier CSV/Excel source: ");
      const output = await prepareContactsFile(source.trim());
      await importContactsToEshelle(output);
    } else {
      console.log("A bientot.");
    }
  } catch (error) {
    console.error("Erreur:", error.message);
    process.exitCode = 1;
  } finally {
    rl.close();
  }
}

main();
