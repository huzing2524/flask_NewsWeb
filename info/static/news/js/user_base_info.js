function getCookie(name) {
    let r = document.cookie.match("\\b" + name + "=([^;]*)\\b");
    return r ? r[1] : undefined;
}

$(function () {

    $(".base_info").submit(function (e) {
        e.preventDefault();

        let signature = $("#signature").val();
        let nick_name = $("#nick_name").val();
        // let gender = $(".gender").val();  错误，取不出女性选择框的值
        let gender = $("input:radio:checked").val();

        if (!nick_name) {
            alert('请输入昵称');
            return
        }
        if (!gender) {
            alert('请选择性别');
        }

        // 修改用户信息接口
        let params = {
            "signature": signature,
            "nick_name": nick_name,
            "gender": gender
        };

        $.ajax({
            url: "/user/base_info",
            type: "post",
            contentType: "application/json",
            headers: {
                "X-CSRFToken": getCookie("csrf_token")
            },
            data: JSON.stringify(params),
            success: function (resp) {
                if (resp.errno == "0") {
                    // 更新父窗口内容
                    $('.user_center_name', parent.document).html(params['nick_name']);
                    $('#nick_name', parent.document).html(params['nick_name']);
                    $('.input_sub').blur()
                } else {
                    alert(resp.errmsg);
                }
            }
        })
    })
});