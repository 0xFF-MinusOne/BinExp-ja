> **これは日本語訳です。**
>
> - 原著: [rosehgal/BinExp](https://github.com/rosehgal/BinExp)(原著者: rosehgal)
> - ライセンス: MIT — 翻訳も同じライセンスです([ライセンス全文](LICENSE))。原文から翻訳(変更)しています
> - 訳した範囲: 全レクチャーの説明文と、コード内の原著者のコメント
> - 訳していないもの: なし
> - 他の日本語訳: [一覧](https://github.com/orgs/0xFF-MinusOne/repositories?q=-ja)

# Binary Exploitation
ほかにも面白いプロジェクトとして @[DockerENT](https://github.com/r0hi7/DockerENT) と @[Trashemail](https://github.com/r0hi7/Trashemail) があります。ぜひ見てみてください。

#### 質問はありますか? [こちらで議論しましょう](https://gitter.im/BinaryExploitation/Lobby?utm_source=share-link&utm_medium=link&utm_campaign=share-link)
> ## はじめに
> 私はバイナリファイルの攻略(exploit)に強い情熱を持っています。初めてバッファオーバーフロー(単純な exploit 手法)に出会ったとき、同じコードを自分のシステムで動かしても、同じ結果を再現できませんでした。
その原因は、システムが変わっても完全な exploit ペイロードを書けるように、最初から丁寧に導いてくれるまとまった資料がなかったことでした。
> また、バイナリを実際に exploit する方法を詳しく解説したブログやチュートリアルも、ほとんどありませんでした。
> そこで、現代的な exploit 手法を(チュートリアルの形で)まとめました。これを読めば、exploit を基礎から理解できます。

仮想マシンの環境構築には [vagrant file](Vagrantfile) を使います。自分のシステムで同じことをするには、次のようにします。
1. `vagrant up`
2. `vagrant ssh`

## トピック

1. **[Lecture 1.](Lecture1/README.md)**
     * C プログラムのメモリレイアウト。
     * ELF バイナリ。
     * 関数呼び出し時のスタックの概要。
     * 関数の呼び出しと復帰のアセンブリコード。
     * `$ebp` と `$esp` の考え方。
     * 実行可能メモリ。

1. **[Lecture 1.5.](Lecture1.5/README.md)**
    * Linux はどのようにしてコマンド(バイナリ)を探し出すのか?
    * Linux の $PATH 変数を使った単純な exploit。

1. **[Lecture 2.](Lecture2/README.md)**
    * スタックオーバーフローとは?
    * **ASLR** (基礎)と、**Stack protection** の回避。
    * シェルコード
    * バッファオーバーフロー:
        *  プログラムの制御を変えて、別の関数に戻らせる
        *  バッファにシェルコードを注入して、シェルを起動する

1. **[Lecture 3.](Lecture3/README.md)**
    * **ASLR** が有効な状態での **シェルコード** 注入。
        * 環境変数。

1. **[Lecture 3.5](Lecture3.5/README.md)**
    * Return to Libc 攻撃。
    * **実行不可スタック** での `shell` の起動。
    * `ret2libc` 攻撃時のスタックの構成。

1. **[Lecture 4.](Lecture4/)**
    * このフォルダには、ここまでに学んだ考え方でバイナリを exploit する問題集が入っています。

1. **[Lecture 5.](Lecture5/README.md)**
    * フォーマット文字列脆弱性とは?
    * スタックの内容を見る。
    * スタックへの書き込み。
    * 任意のメモリ位置への書き込み。

1. **[Lecture 6.](Lecture6/README.md)**
    * GOT
    * GOT エントリの上書き。
    * フォーマット文字列脆弱性でシェルを起動する。

1. **[Lecture 7.](Lecture7/README.md)**
    * ヒープ
    * Arena、Bin、チャンク。
    * Use after free の exploit。
    * Double free の exploit。
