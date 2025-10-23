# finalproject_bulankin_M25-555

### Тестовый сценарий

```bash
register
login
show-portfolio
buy
sell
get-rate
register --username alice --password 123
register --username alice --password 1234
register --username alice --password 1234
login --username alice1234 --password 1234
login --username alice --password 123
login --username alice --password 1234
show-portfolio
buy --currency BTC --amount 250
get-rate --from ETH --to BTC
show-rates
update-rates
sell --currency ETH --amount 3
buy --currency USD --amount 30000
buy --currency ETH --amount 112
sell --currency ETH --amount 12.5
sell --currency ETH --amount 100.7
show-portfolio
sell --currency ABC --amount 1
get-rate --from ETH --to BTC
get-rate --from USD --to BTC
get-rate --from ETH --to SOL
get-rate --from ETH --to ABC
show-portfolio --base USD
show-portfolio --base ABC
show-portfolio --base BTC
show-rates
show-rates --top 2
show-rates --currency RUB

register --username professor --password 12345
login --username professor --password 12345
show-portfolio
buy --currency RUB --amount 1000
sell --currency RUB --amount 500
show-portfolio
login --username alice --password 1234
show-portfolio
```

## Запись Asciinema
[![asciicast](https://asciinema.org/a/g6QEW7vAP490ndAe5Rk3ZgdtL.svg)](https://asciinema.org/a/g6QEW7vAP490ndAe5Rk3ZgdtL)
