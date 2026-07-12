# Raw data policy

Do not place portfolio source data in this repository.

Keep the six CSV files in an external directory and run:

```bash
make full DATA_DIR=/absolute/path/dataset
```

Required filenames:

```text
users.csv
products.csv
orders.csv
user_behaviors.csv
user_features.csv
product_features.csv
```

The current external dataset has no verified source or license and appears synthetic. It must not be described as real company, Taobao, Alibaba, or production data. See [`../../DATASET_NOTICE.md`](../../DATASET_NOTICE.md) for the exact headers and publication rules.
