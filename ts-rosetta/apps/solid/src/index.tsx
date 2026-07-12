/* @refresh reload */
import { render } from 'solid-js/web';
import '@rosetta/core/styles.css';
import Board from './Board';

render(() => <Board />, document.getElementById('root')!);
