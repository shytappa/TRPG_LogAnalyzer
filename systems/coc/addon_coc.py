"""
CoC の画面に、後から機能を足すための差し込み口（自卓用の履歴・PLモード・PL統計など）。

通常版の処理（app_coc.py）は、ここに書いた関数を決まった場所で呼ぶだけで、足す機能の中身は知らない。
機能を足すときは CocAddon を継承して必要な関数だけを書き換え、プロファイルの addon に渡す
（例: systems/coc_shy/addon_shy.py を pages/pages_coc_shy.py で渡している）。
足す側のファイルを丸ごと外しても、通常版はそのまま動く。
"""


class CocAddon:
    """何もしない差し込み口（通常版はこれを使う）。各関数の説明が、通常版の処理から呼ばれる場所と使い方"""

    # 「設定をリセット」で消さないキーの頭の部分（読み込んだデータなど）
    reset_keep_keys = ()
    # 読み込んだログが入っているキー（ページを移るときに「消えます」と確認する）
    data_keys = ()
    # 描画しない回も値を残すキーの頭の部分（閉じたタブの中の設定など。app_coc._keep_hidden_settings で書き戻す）
    keep_prefixes = ()
    # ログを ✖ で消したときに一緒に消すキーの頭の部分。実際のキーは「頭の部分 + logic_base.make_key(ログ名, '')」
    per_log_prefixes = ()

    def file_sources(self):
        """サイドバーのファイル管理に、アップロード以外の読み込み元を並べる（表示名 → ✖で消すときに呼ぶ関数）"""
        return {}

    def render_sidebar(self):
        """サイドバーのファイル管理のすぐ下に、欄を足す"""

    def load_key(self):
        """ログを読み込み直すかの判断に足すもの（ここが変わると読み込み直す。ファイルの更新時刻など、軽く作れるもの）"""
        return ()

    def read_logs(self, uploaded_names):
        """
        アップロードしたログに加えて読み込むログ。
        uploaded_names: アップロードしたログのファイル名（同じ名前のログを区別するのに使う）
        戻り値: (表のリスト, 読み込みに関する注意のリスト, 読み込み元の表示名 → その中のログのファイル名の集合)
        """
        return [], [], {}

    def after_read(self, df):
        """読み込んだ全ログの表への後処理（キャラ名の表記ブレをまとめるなど）。表を返す"""
        return df

    def select_rows(self, full_df):
        """
        サイドバーの絞り込みの前に、表示を切り替えたり行を絞ったりする（サイドバーに欄を出してよい）。
        戻り値: (表, view)。view は下の関数にそのまま渡す値（何を入れるかは足す側で決める）。表が空なら、そこで止まる
        """
        return full_df, None

    def after_filters(self, df_filtered, view):
        """サイドバーの絞り込み・キャラクターの統合が終わった後の表に、表示のための手を加える（名前に印を付けるなど）。表を返す"""
        return df_filtered

    def summary_default_sort(self, view):
        """総合サマリーの行の並び順の初期値（列のキー, 順序）。None なら通常どおり（名前順）"""
        return None

    def extra_tabs(self, df_filtered, recalc_rule, view):
        """ダッシュボードに足すタブ: [(タブの見出し, エラーの案内での呼び名, 中身を描画する関数), ...]"""
        return []

    # 以下は「📉 パラメータ増減」のタブを開いたときだけ呼ばれる
    def param_log_files(self):
        """
        アップロードしたログに加えて読むログ（ファイル名 → 中身）。
        ファイル名は read_logs の表の「ファイル名」と同じにする（ステータスの変化の記録の名前を、画面の名前に揃えるため）
        """
        return {}

    def fix_param_changes(self, changes):
        """
        ログから読んだステータスの変化（features/params/logic_params.extract の形）に、足す機能の側で保存してある直しを当てて返す
        （自卓用ならマッピングツールで保存した直し。systems/coc_shy/param_fixes.py）。通常版は何もしない
        """
        return changes

    def param_rows(self, full_df, view):
        """
        ステータスの変化を数えるキャラを決める表（この表の行のキャラだけを数え、その行の「キャラクター名」で表示する）。
        view は select_rows が返したもの
        """
        return full_df

    def param_show_start_end(self, view):
        """SAN の開始・終了の列を出すか（1行に何人もの探索者をまとめる表示では、開始・終了に意味が無いので出さない）"""
        return True


NO_ADDON = CocAddon()
