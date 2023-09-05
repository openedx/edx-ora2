const fs = require('fs');

const newVersion = process.argv[2];

// Replace the version number in __init__.py
const initFile = "openassessment/__init__.py";
fs.readFile(initFile, "utf8", (err, content) => {
  if (err) {
    console.error(`Error reading ${initFile}:`, err);
    process.exit(1);
  }

  const updatedContent = content.replace(/__version__ = '[\d.]*'/, `__version__ = '${newVersion}'`);

  fs.writeFile(initFile, updatedContent, "utf8", (err) => {
    if (err) {
      console.error(`Error writing to ${initFile}:`, err);
      process.exit(1);
    }
    console.log(`Updated ${initFile} with version ${newVersion}`);
  });
});
