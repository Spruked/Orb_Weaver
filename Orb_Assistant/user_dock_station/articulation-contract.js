const fs = require('fs');
const path = require('path');

const INCULCATION_PATH = path.resolve(__dirname, '../../artifacts/inculcation.md');
const ORB_ARTICULATION_CONTRACT = fs.readFileSync(INCULCATION_PATH, 'utf8');

function buildOwnerBehaviorInstruction(profile) {
  void profile;
  return ORB_ARTICULATION_CONTRACT;
}

module.exports = {
  ORB_ARTICULATION_CONTRACT,
  buildOwnerBehaviorInstruction
};
