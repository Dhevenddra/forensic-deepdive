// NestJS controller (DEC-062) — @Controller prefix + verb-decorated methods.
@Controller('cats')
export class CatsController {
  @Get(':id')
  findOne(id) {
    return id;
  }

  @Post()
  create() {}
}
