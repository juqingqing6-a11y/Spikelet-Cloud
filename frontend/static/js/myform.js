
$("#myForm").submit(function (event) {
    event.preventDefault(); // 阻止表单的默认提交行为
    $.ajax({
        url: "/submit_form/", // Django视图函数的URL
        type: "POST",
        data: $(this).serialize(), // 序列化表单数据
        dataType: "json",
        success: function (response) {
            $("#message").html(response.message); // 显示服务器返回的消息
        },
        error: function () {
            $("#message").html("An error occurred.");
        }
    });
});