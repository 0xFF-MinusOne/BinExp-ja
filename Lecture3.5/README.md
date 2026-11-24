# Return 2 Libc 攻撃
`ret2libc` 攻撃は、次のような状況で成立します。
    * メモリが実行 **不可** である。
    * スタック保護が **無効** である。
    * Stack canary が **無効** である。
    * ASLR に依存しない。

名前が示すとおり、この攻撃はバッファをあふれさせて、戻りアドレスを共有ライブラリ(`libc`)内の関数のアドレスに書き換えます。この攻撃で学ぶべき主な点は、return 命令が本物の CALL 命令のふりをしなければならないとき、スタックをどのように細工する必要があるかを理解することです。そのためには、関数呼び出し時にスタックがどう並ぶかを理解する必要があります。それについては、この[講義](../Lecture1/README.md)を読んでください。

```
                        +   Previous function  |
                        |     Stack frame      |
                        |                      |
                        +----------------------+ <--- previous function stack frame end here
                        |Space for return value|
                        +----------------------+
                        |Arguments for function|
                        +----------------------+
                        |    return address    |
                        +----------------------+
                        |     saved $ebp       |
                        +----------------------+
                        |                      | <---  padding done by compilers
                        +----------------------+
                        |    local variables   |

```
これは、新しい関数のフレームが作られたときのスタックの様子です。この関数から戻り始めるときには、次のようになるでしょう。
```
                   +   Pre^ious function  +  +   Pre^ious function  +
                   |     Stack frame      |  |     Stack frame      |
                   |                      |  |                      |
Previous fn+---->  +----------------------+  +----------------------+
                   |Space for return ^alue|  |space for return value|
                   +----------------------+  +----------------------+
                   |Arguments for function|  |Arguments for function|
                   +----------------------+  +----------------------+
                   |    return address    |  |                      |
                   +----------------------+  +----------------------+
                   |     sa^ed $ebp       |  |                      |
                   +----------------------+  +----------------------+
                   |                      |  |                      |
                   +----------------------+  |                      |
                   |    local variables   |  |                      |

```
制御は前の関数には戻らず、`CALL` 命令の既定の動作のように、別の関数へ移ります。新しい関数は、自分が通常どおり呼び出されたものと想定します。前の講義で、CALL の前の命令、CALL、CALL の後の命令という3つの別々のものに分類しました。現在のスタックでも、それと同じ効果を作らなければなりません。
```
      prev                                                                next
+-----------------+                                               +-----------------+
|                 |                                               |                 |
|1. ret val space |                                               |1. pushes ebp    |
|2. arguments     | +------------->CALL Inst +------------------> |2. updates ebp   |
|                 |                    +                          |                 |
|                 |                    v                          |                 |
+-----------------+       Pushes the return address               +-----------------+
```

この現在の関数は、次のことを想定します。
    1. 戻り値の領域と引数の領域は、すでに取り除かれている。
    2. 新しい関数の領域と戻りアドレスは、すでにスタックに push されている。
    3. 新しい戻りアドレスは、すでにスタックに push されている。
そのほかの命令は、次の関数が自分のコードの中で処理します。実際には return 命令なので、こうしたことは何も起きていません。そのため、通常の関数呼び出しだった場合と同じに見えるようスタックを作る必要があります。ただし今のところ、戻った場合のスタックは次のようになると分かっています。
```
                +   Pre^ious function  +
                |     Stack frame      |
                |                      |
                +----------------------+
                |space for return value|
                +----------------------+
                |Arguments for function|
                +----------------------+
                |                      |
                +----------------------+
                |                      |
                +----------------------+
                |                      |
                |                      |

```
制御が次の関数に移ると、その関数は `$ebp` を push します。次の関数から見ると、スタックは次のように見えなければなりません。
```
                +   Pre^ious function  ++   Pre^ious function  +
                |     Stack frame      ||     Stack frame      |
                |                      ||                      |
                +----------------------++----------------------+
                |space for return value||space for return value|
                +----------------------++----------------------+
                |Arguments for function||Arguments for function|
                +----------------------++----------------------+
                |                      ||       $ebp           |
                +----------------------++----------------------+
                |                      ||       padding        |
                +----------------------++----------------------+
                |                      ||                      |

```
次の関数のスタックは、次のようになります。次の関数は、`$ebp` の上に戻りアドレスがあるはずだと知っているので、`argument previous function`(前の関数の引数)を、この関数の `return address`(戻りアドレス)とみなします。
```
                   The actual stack              The way next see stack


                +   Pre^ious function  +      +   Pre^ious function  +
                |     Stack frame      |      |     Stack frame      |
                |                      |      |Space for return value|
                +----------------------+      +----------------------+
                |space for return value|      | Arguments to function|
                +----------------------+      +----------------------+
                |Arguments for function|      |    return address    |
                +----------------------+      +----------------------+
                |       $ebp           |      |       $ebp           |
                +----------------------+      +----------------------+
                |       padding        |      |       padding        |
                +----------------------+      +----------------------+
                |                      |      |                      |
                |                      |      |                      |

```
最初の図と最後の図を比べると、スタックが4バイトずれているように見えます。
```
                    Actual Stack                    How next see it


                +   Pre^ious function  +       +   Pre^ious function  +
                |     Stack frame      |       |     Stack frame      |
                |                      |       |Space for return value|
                +----------------------+       +----------------------+
                |Space for return ^alue|       | Arguments to function|
                +----------------------+       +----------------------+
                |Arguments for function|       |    return address    |
                +----------------------+       +----------------------+
                |    return address    |       |       $ebp           |
                +----------------------+       +----------------------+
                |     sa^ed $ebp       |       |       padding        |
                +----------------------+       +----------------------+
                |                      |       |                      |

```
バッファオーバーフローは、次の関数から見たスタックが2番目の図のように見えるように、スタックを上書きしなければなりません。

#### Return 2 libc を実行する

`system` を呼ぶためにスタックを上書きする方法も同じ考え方に従います。この場合、ここまで話してきた `next`(次の)関数が `system` になります。プログラムを正常に終了させるために、system の戻りアドレスには `exit` の呼び出しを指定します。:smile: `system` からのもう1つの `return2lib` です。
exploit のペイロードは、次のようになります。
``echo -e `python -c "import struct; print 'A'*108 + 'BBBB' + 'CCCC' + struct.pack('<I', <address of system>) + struct.pack('<I', <address of exit>) + <Address of argument to system>"` ``

次にすることは、シェルを起動するために、`system` と `exit` のアドレス、そして `system` への引数(`"/bin/sh"`)のアドレスを見つけることです。`system` と `exit` のアドレスは `GDB` で調べられます。しかし、プログラムの中にすら存在しない文字列 `"/bin/sh"` のアドレスは、どうやって得ればよいでしょうか。
ここでも環境変数が役に立ちます。環境変数もスタックの上のほうに積まれるからです。次のように環境変数を1つ作ります。
`export SHELL="/bin/sh"`
GDB を実行して、`$esp` から、たとえば500個の文字列エントリを表示します。
`gef> x/100s $esp`
そして、その文字列がどこにあるかを確認します。これで必要なアドレスがすべてそろったので、exploit のテンプレートを埋めます。:cool: これも達成できました。

#### 学んだこと
ある関数から戻ることで別の関数の呼び出しを真似るには、スタックが1つ(4バイト)ずれます。そのため、exploit のペイロードには余分に4バイトの 'CCCC' が加えられています。
また、この exploit では ASLR による保護を回避できます。
