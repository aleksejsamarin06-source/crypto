# CryptoSafe Manager Test Report

Generated: 2026-06-04T02:19:33
Exit code: 0
Coverage: 82%

## Command

```text
C:\Users\Lecoo\PycharmProjects\crypto\.venv\Scripts\python.exe -m pytest --cov=src --cov-report=term-missing --cov-report=html:tests/report/coverage_html --cov-report=json:tests/report/coverage.json
```

## Pytest Output

```text
........s...............................................                 [100%]
============================== warnings summary ===============================
tests/test_clipboard_integration.py: 2 warnings
tests/test_entry_manager.py: 200 warnings
tests/test_import_export_sprint6.py: 26 warnings
  C:\Users\Lecoo\PycharmProjects\crypto\src\core\vault\entry_manager.py:32: DeprecationWarning: The default datetime adapter is deprecated as of Python 3.12; see the sqlite3 documentation for suggested replacement recipes
    cursor.execute(

tests/test_entry_manager.py: 50 warnings
  C:\Users\Lecoo\PycharmProjects\crypto\src\core\vault\entry_manager.py:97: DeprecationWarning: The default datetime adapter is deprecated as of Python 3.12; see the sqlite3 documentation for suggested replacement recipes
    cursor.execute(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=============================== tests coverage ================================
_______________ coverage: platform win32, python 3.14.3-final-0 _______________

Name                                                 Stmts   Miss  Cover   Missing
----------------------------------------------------------------------------------
src\core\audit\__init__.py                               0      0   100%
src\core\audit\audit_logger.py                         104     21    80%   23-36, 40, 75, 137, 144, 152, 158, 164
src\core\audit\log_formatters.py                        72     24    67%   60, 71-100
src\core\audit\log_signer.py                            42      1    98%   64
src\core\audit\log_verifier.py                         107     23    79%   22-30, 81, 85-89, 93-98, 140-144, 155, 165, 173, 192, 211
src\core\clipboard\__init__.py                           0      0   100%
src\core\clipboard\clipboard_service.py                 95     25    74%   13, 18-19, 49, 65-67, 82-84, 104-106, 109-116, 119, 122-124
src\core\crypto\__init__.py                              0      0   100%
src\core\crypto\abstract.py                              5      2    60%   3, 6
src\core\crypto\authentication.py                       65     13    80%   20, 30, 51, 53, 85-94, 103, 112
src\core\crypto\key_derivation.py                       39      1    97%   73
src\core\crypto\key_storage.py                          46      8    83%   31-32, 51-53, 59, 61-62
src\core\crypto\placeholder.py                          12      0   100%
src\core\events.py                                      17      3    82%   15-16, 19
src\core\import_export\__init__.py                       5      0   100%
src\core\import_export\crypto_utils.py                  96     13    86%   40, 62, 125, 129, 132, 139, 146, 194, 198, 201, 206-208
src\core\import_export\exporter.py                      77     23    70%   32-34, 36-37, 45-47, 60-66, 80, 85-86, 99, 111-115
src\core\import_export\formats\__init__.py               3      0   100%
src\core\import_export\formats\csv_format.py            23      2    91%   21-22
src\core\import_export\formats\password_manager.py      23      1    96%   48
src\core\import_export\importer.py                     146     35    76%   30-35, 51, 60, 65-66, 68-70, 101, 108, 110, 113-115, 121-128, 135, 142, 148, 150, 153, 180-182, 187
src\core\import_export\key_exchange.py                  98     31    68%   24-25, 28-37, 40-48, 97, 121, 124, 129, 132, 137-138, 141-150
src\core\import_export\sharing_service.py               69     16    77%   26, 29, 32-34, 38, 62-63, 81, 88, 92, 97-99, 106, 113
src\core\key_manager.py                                 49      0   100%
src\core\security\__init__.py                            5      0   100%
src\core\security\activity_monitor.py                   47      3    94%   27, 44-45
src\core\security\memory_guard.py                       71     16    77%   18-19, 30-34, 40-44, 48, 51, 59, 65
src\core\security\panic_mode.py                         25      4    84%   28-29, 34-35
src\core\security\side_channel_protection.py            38      1    97%   31
src\core\settings_manager.py                            85      3    96%   20, 95-96
src\core\vault\__init__.py                               0      0   100%
src\core\vault\encryption_service.py                    31      2    94%   15, 28
src\core\vault\entry_manager.py                         70     11    84%   38-40, 58, 74, 102-104, 115-117
src\core\vault\password_generator.py                    63      8    87%   21, 23, 52, 77-88
src\database\db.py                                      90     26    71%   22, 182-199, 204, 212-221, 225-254
----------------------------------------------------------------------------------
TOTAL                                                 1718    316    82%
Coverage HTML written to dir tests/report/coverage_html
Coverage JSON written to file tests/report/coverage.json
Required test coverage of 80% reached. Total coverage: 81.61%
55 passed, 1 skipped, 278 warnings in 14.99s

```