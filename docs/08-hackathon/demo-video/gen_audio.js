const { execSync } = require("child_process");
const fs = require("fs");
const path = require("path");
const segments = require("./segments");

const AUDIO_DIR = path.join(__dirname, "audio");
fs.mkdirSync(AUDIO_DIR, { recursive: true });

const durations = {};

for (const seg of segments) {
  const wavPath = path.join(AUDIO_DIR, `${seg.id}.wav`);
  // espeak-ng: -s 150 (words/min, natural-ish pace), -v en-us
  execSync(
    `espeak-ng -v en-us -s 150 -w "${wavPath}" "${seg.narration.replace(/"/g, '\\"')}"`,
    { stdio: "inherit" }
  );
  const probe = execSync(
    `ffprobe -v error -show_entries format=duration -of csv=p=0 "${wavPath}"`
  )
    .toString()
    .trim();
  durations[seg.id] = parseFloat(probe);
  console.log(`${seg.id}: ${durations[seg.id].toFixed(2)}s`);
}

fs.writeFileSync(
  path.join(__dirname, "durations.json"),
  JSON.stringify(durations, null, 2)
);
console.log("\nTotal narration:", Object.values(durations).reduce((a, b) => a + b, 0).toFixed(1), "s");
