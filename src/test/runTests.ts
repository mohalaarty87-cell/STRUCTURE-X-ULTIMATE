import { runAllVerificationSuites } from './testRunner';

console.log('================================================================');
console.log(' STRUCTURE-X ULTIMATE — PHASE 01 FOUNDATION VERIFICATION SUITE');
console.log('================================================================\n');

const report = runAllVerificationSuites();

report.suites.forEach(suite => {
  console.log(`\n📦 Suite: ${suite.name}`);
  suite.tests.forEach(t => {
    const icon = t.passed ? '  ✅ PASS' : '  ❌ FAIL';
    console.log(`${icon} : ${t.name}`);
    if (t.message) {
      console.log(`      ↳ Error: ${t.message}`);
    }
  });
});

console.log('\n----------------------------------------------------------------');
console.log(` Summary: ${report.passedCount}/${report.totalTests} Passed | ${report.failedCount} Failed`);
console.log(` Result:  ${report.allPassed ? 'ALL TESTS PASSED ✨' : 'TESTS FAILED ⚠️'}`);
console.log('----------------------------------------------------------------\n');

if (!report.allPassed) {
  process.exit(1);
}
