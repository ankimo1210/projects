import { Component, signal } from '@angular/core';
import { TasksComponent } from './tasks.component';
import { BoardComponent } from './board.component';

// Tiny hash "router": #board shows the live board, anything else the tasks app.
@Component({
  selector: 'app-root',
  imports: [TasksComponent, BoardComponent],
  template: `
    @if (view() === 'board') {
      <app-board />
    } @else {
      <app-tasks />
    }
  `,
})
export class AppComponent {
  readonly view = signal(location.hash === '#board' ? 'board' : 'tasks');

  constructor() {
    addEventListener('hashchange', () =>
      this.view.set(location.hash === '#board' ? 'board' : 'tasks'),
    );
  }
}
