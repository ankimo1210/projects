import { IsString, IsNotEmpty } from 'class-validator';

/** Request body for POST /tasks. Validated by the global ValidationPipe. */
export class CreateTaskDto {
  @IsString()
  @IsNotEmpty()
  title: string;
}
