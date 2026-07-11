// NestJS: the same API as server-express, but structured. Nothing here
// mentions routes — those live in the controller; state lives in the
// service; validation lives in DTO classes. DI wires them together.
import 'reflect-metadata';
import { NestFactory } from '@nestjs/core';
import { ValidationPipe } from '@nestjs/common';
import { AppModule } from './app.module';

const PORT = 4001;

async function bootstrap() {
  const app = await NestFactory.create(AppModule);
  app.enableCors();
  // Rejects unknown fields and enforces DTO decorators globally.
  app.useGlobalPipes(new ValidationPipe({ whitelist: true, forbidNonWhitelisted: true }));
  await app.listen(PORT);
  console.log(`[nest] listening on http://localhost:${PORT}`);
}

void bootstrap();
