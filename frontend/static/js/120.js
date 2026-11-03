// 获取要操作的元素
let items=document.querySelectorAll('.item');


// 设置选中项的样式
function setActive(){
    items.forEach((item)=>{
        item.classList.remove('active');
    })
    this.classList.add('active');
    // current_tag.innerText=this.innerText;
}
// 为每一个li设置点击事件
items.forEach((item)=>{
    item.addEventListener('click',setActive);
})

