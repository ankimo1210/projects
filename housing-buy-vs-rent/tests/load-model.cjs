const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

module.exports = function loadModel() {
  const source = fs.readFileSync(path.join(__dirname, '../current/source/extracted_scripts.js'), 'utf8');
  const context = vm.createContext({});
  vm.runInContext(source.split('// ===== script block 4 =====')[0] +
    '\nglobalThis.loaded={M:HousingModel,S:HousingSensitivity,p:BASE_PARAMS,I:typeof HousingInputs===\'undefined\'?undefined:HousingInputs}', context);
  return context.loaded;
};
