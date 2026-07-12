import {
  Controller,
  Get,
  Post,
  Patch,
  Delete,
  Param,
  Body,
  HttpCode,
} from '@nestjs/common';
import type { Task, Stats } from '@rosetta/core';
import { TasksService } from './tasks.service';
import { CreateTaskDto } from './dto/create-task.dto';
import { UpdateTaskDto } from './dto/update-task.dto';

/**
 * Routing is declared with decorators; the service arrives via
 * constructor injection. Same HTTP contract as server-express.
 */
@Controller()
export class TasksController {
  constructor(private readonly tasksService: TasksService) {}

  @Get('tasks')
  findAll(): Task[] {
    return this.tasksService.findAll();
  }

  @Get('stats')
  stats(): Stats {
    return this.tasksService.stats();
  }

  @Post('tasks')
  create(@Body() dto: CreateTaskDto): Task {
    return this.tasksService.create(dto.title);
  }

  @Patch('tasks/:id')
  setDone(@Param('id') id: string, @Body() dto: UpdateTaskDto): Task {
    return this.tasksService.setDone(id, dto.done);
  }

  @Delete('tasks/:id')
  @HttpCode(204)
  remove(@Param('id') id: string): void {
    this.tasksService.remove(id);
  }
}
