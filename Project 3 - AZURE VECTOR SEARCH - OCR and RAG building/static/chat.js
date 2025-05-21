document.addEventListener("DOMContentLoaded", () => {
  const textBtn = document.getElementById("textBtn");
  const recordContainer = document.getElementById("recordBtnContainer");

  async function callgpt(user_question) {
    const response = await fetch("/rispostacompliance", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({user_question: user_question})
    });

    const data = await response.json();
    if (response.ok && data.success) {
      return data;
    }
  }

  async function getAndSendText() {
    const user_slot = document.getElementById('inputBox');
    const user_question = user_slot.value;
    user_slot.value = "";
    await createUserSlots(user_question);
    const data = await callgpt(user_question);
    await createGptSlots(data);
  }

  async function createUserSlots(user_question) {
    const chatSection = document.getElementById("responseArea");

    // BUILD
    const user_slot = document.createElement("div");
    const user_div = document.createElement("div");

    // STYLE
    user_slot.setAttribute("class", "user_input");
    user_div.setAttribute("class", "user_text");
    user_div.innerText = user_question;

    // POSITION
    user_slot.append(user_div);
    chatSection.append(user_slot);
  }


  // DYNAMIC HTML CREATION
  async function createGptSlots(data) {
    const chatSection = document.getElementById("responseArea");

    // BUILD
    const gptMainSlot = document.createElement("div");
    const gpt_div = document.createElement("div");

    // STYLE
    gptMainSlot.setAttribute("class", "gptMainSlot");
    gpt_div.setAttribute("class", "gpt_output");

    gpt_links = data.list_url;

    const link1 = gpt_links[0]
    const link2 = gpt_links[1]
    const link3 = gpt_links[2]

    console.log(link1)

    const linkSlot = await createLinkSlot(link1, link2, link3);

    gpt_div.innerText = data.gpt_response;

    // POSITION
    chatSection.append(gptMainSlot)
    gptMainSlot.append(gpt_div);
    gptMainSlot.append(linkSlot);
  }


  async function createLinkSlot(link1, link2, link3) {

    // BUILD
    const linkSlot = document.createElement("div");

    const linkSlot1 = document.createElement("a");
    const linkSlot2 = document.createElement("a");
    const linkSlot3 = document.createElement("a");

    // STYLE
    linkSlot.setAttribute("class", "linkcontainer");
    linkSlot1.setAttribute("class", "linkSlot");
    linkSlot2.setAttribute("class", "linkSlot");
    linkSlot3.setAttribute("class", "linkSlot");

    linkSlot1.innerText = link1;
    linkSlot2.innerText = link2;
    linkSlot3.innerText = link3;

    linkSlot1.setAttribute("href", link1);
    linkSlot2.setAttribute("href", link2);
    linkSlot3.setAttribute("href", link3);

    // POSITION
    linkSlot.append(linkSlot1);
    linkSlot.append(linkSlot2);
    linkSlot.append(linkSlot3);

    return linkSlot
  }

  textBtn.addEventListener("click", getAndSendText);
});
