import { IsBoolean } from 'class-validator';

/** Request body for PATCH /tasks/:id. */
export class UpdateTaskDto {
  @IsBoolean()
  done: boolean;
}
