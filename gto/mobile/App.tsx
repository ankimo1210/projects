import { StatusBar } from 'expo-status-bar';
import { StyleSheet, Text, View } from 'react-native';
import { canonicalizeBoard, comboIndex, parseCard, NUM_COMBOS } from '@gto/domain';

// Temporary wiring proof for the P1 scaffold: renders values computed by
// @gto/domain so a Simulator boot demonstrates the workspace package resolves
// through Metro. Replaced by the Study tab in the next P1 increment.
const DEMO_FLOP = ['As', 'Kd', '7c'];

export default function App() {
  const canon = canonicalizeBoard(DEMO_FLOP);
  const aksCombo = comboIndex(parseCard('As'), parseCard('Ks'));
  return (
    <View style={styles.container}>
      <Text style={styles.title}>GTO — P1 scaffold</Text>
      <Text style={styles.line}>
        canon({DEMO_FLOP.join(' ')}) = {canon}
      </Text>
      <Text style={styles.line}>
        comboIndex(AsKs) = {aksCombo} / {NUM_COMBOS}
      </Text>
      <StatusBar style="auto" />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0f172a',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
  },
  title: {
    color: '#f8fafc',
    fontSize: 20,
    fontWeight: '700',
  },
  line: {
    color: '#94a3b8',
    fontSize: 14,
    fontVariant: ['tabular-nums'],
  },
});
